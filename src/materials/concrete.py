"""
콘크리트 재료 모델

KDS 24 14 21:2025 식 (3.1-38)~(3.1-42) 기반
포물선-직선형 응력-변형률 관계 구현
"""
import numpy as np
from .base import Material


class Concrete(Material):
    """
    콘크리트 재료 클래스

    지원 곡선 유형:
      - "parabolic_rectangular" : KDS/EC2 기본 포물선-직선형 (기본값)
      - "linear"                : 선형 탄성 (개략 검토용)
      - "bilinear"              : 이선형 근사
    """

    PARABOLIC_RECT = "parabolic_rectangular"
    LINEAR = "linear"
    BILINEAR = "bilinear"

    def __init__(
        self,
        fck: float,
        *,
        fcd: float = None,
        gamma_c: float = 0.65,
        alpha_cc: float = 1.0,
        curve_type: str = "parabolic_rectangular",
    ):
        """
        Args:
            fck      : 기준압축강도 [MPa]
            fcd      : 설계압축강도 [MPa]  ← 직접 입력 시 gamma_c/alpha_cc 무시
            gamma_c  : 콘크리트 재료계수
                       KDS ULS = 0.65 / EC2 ULS = 1.5 / ACI = 1.0
            alpha_cc : 유효계수 (일반 1.0, 쪼갬인장강도 산정 시 0.85)
            curve_type: 응력-변형률 곡선 유형
        """
        self.fck = fck
        self.gamma_c = gamma_c
        self.alpha_cc = alpha_cc
        self.curve_type = curve_type

        # ── 설계압축강도  fcd = αcc·fck / γc  (식 3.1-47) ──────────
        self.fcd = fcd if fcd is not None else alpha_cc * fck / gamma_c

        # ── 평균압축강도  fcm (식 3.1-1) ────────────────────────────
        # fck ≤ 50 MPa → Δ = 8 MPa / fck > 50 MPa → Δ = 4 MPa
        self.fcm = fck + (8.0 if fck <= 50.0 else 4.0)

        # ── 응력-변형률 파라미터 (KDS 표 3.1-1 해당) ─────────────────
        self._set_strain_params()

    # ──────────────────────────────────────────────────────────────────
    # 내부 초기화
    # ──────────────────────────────────────────────────────────────────
    def _set_strain_params(self):
        """KDS 24 14 21 식 (3.1-40)~(3.1-42) 기반 변형률 파라미터 결정"""
        fck = self.fck
        if fck <= 50.0:
            self.n   = 2.0
            self.ec1 = 2.0e-3   # 정점변형률 εc1
            self.ecu = 3.5e-3   # 극한압축변형률 εcu
        else:
            # 고강도 콘크리트 50 < fck ≤ 90 MPa
            x = (90.0 - fck) / 100.0
            self.n   = 1.4 + 23.4 * x ** 4                           # 식 3.1-42
            self.ec1 = (2.0 + 0.085 * (fck - 50.0) ** 0.53) * 1e-3  # 식 3.1-40
            self.ecu = (2.6 + 35.0 * x ** 4) * 1e-3                  # 식 3.1-41

    # ──────────────────────────────────────────────────────────────────
    # Material 인터페이스 구현
    # ──────────────────────────────────────────────────────────────────
    def stress(self, strain: float) -> float:
        """
        압축 변형률(+) → 양수 응력 반환
        인장(strain < 0) → 0 반환  (인장강도 무시)
        극한변형률 초과 → 0 반환  (압괴 처리)
        """
        if strain <= 0.0:
            return 0.0

        funcs = {
            self.PARABOLIC_RECT: self._parabolic_rect,
            self.LINEAR:         self._linear,
            self.BILINEAR:       self._bilinear,
        }
        return funcs.get(self.curve_type, self._parabolic_rect)(strain)

    def elastic_modulus(self) -> float:
        """
        KDS 24 14 21 식 (3.1-10)
        Ecm = 22 × (fcm/10)^0.3 × 10³  [MPa]
        """
        return 22.0 * (self.fcm / 10.0) ** 0.3 * 1_000.0

    @property
    def label(self) -> str:
        return f"Concrete fck={self.fck:.0f} MPa (fcd={self.fcd:.1f})"

    # ──────────────────────────────────────────────────────────────────
    # 개별 응력-변형률 곡선 구현
    # ──────────────────────────────────────────────────────────────────
    def _parabolic_rect(self, eps: float) -> float:
        """
        KDS 24 14 21 식 (3.1-38), (3.1-39)
          0 ≤ εc ≤ εc1 : σc = fcd × [1 - (1 - εc/εc1)^n]
          εc1 < εc ≤ εcu: σc = fcd
          εc > εcu      : σc = 0 (압괴)
        """
        if eps <= self.ec1:
            return self.fcd * (1.0 - (1.0 - eps / self.ec1) ** self.n)
        elif eps <= self.ecu:
            return self.fcd
        else:
            return 0.0   # 극한변형률 초과 → 압괴

    def _linear(self, eps: float) -> float:
        """선형 탄성 (fcd에서 제한)"""
        return min(self.elastic_modulus() * eps, self.fcd)

    def _bilinear(self, eps: float) -> float:
        """이선형 근사 (기울기 E → 수평선 fcd)"""
        knee = self.fcd / self.elastic_modulus()
        if eps <= knee:
            return self.elastic_modulus() * eps
        elif eps <= self.ecu:
            return self.fcd
        else:
            return 0.0

    # ──────────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"Concrete(fck={self.fck}, fcd={self.fcd:.2f}, "
            f"εc1={self.ec1*1e3:.2f}‰, εcu={self.ecu*1e3:.2f}‰, n={self.n:.2f})"
        )
