"""
철근(Rebar) 재료 모델

KDS 24 14 21:2025 § 3.2 기반
설계항복강도: fyd = fy / γs  (γs = 0.90 for ULS)
탄성계수:     Es = 200,000 MPa
"""
import numpy as np
from .base import Material


class Rebar(Material):
    """
    철근 재료 클래스

    지원 곡선 유형:
      - "elastic_perfectly_plastic" : 완전 탄소성 (기본값, 가장 일반적)
      - "bilinear_hardening"        : 변형경화 포함 이선형
    """

    EPP = "elastic_perfectly_plastic"
    BLH = "bilinear_hardening"

    def __init__(
        self,
        fy: float,
        *,
        fyd: float = None,
        Es: float = 200_000.0,
        gamma_s: float = 0.90,
        esu: float = 0.025,
        hardening_ratio: float = 0.01,
        curve_type: str = "elastic_perfectly_plastic",
    ):
        """
        Args:
            fy              : 기준항복강도 [MPa]
            fyd             : 설계항복강도 [MPa] ← 직접 입력 시 gamma_s 무시
            Es              : 탄성계수 [MPa]  (기본 200,000 MPa)
            gamma_s         : 철근 재료계수  (KDS ULS = 0.90, EC2 = 1.15, ACI = 1.0)
            esu             : 극한(파단) 변형률
            hardening_ratio : 변형경화 기울기 비율 (BLH 곡선 전용, E × ratio)
            curve_type      : 응력-변형률 곡선 유형
        """
        self.fy = fy
        self.Es = Es
        self.gamma_s = gamma_s
        self.esu = esu
        self.hardening_ratio = hardening_ratio
        self.curve_type = curve_type

        # 설계항복강도  fyd = fy / γs
        self.fyd = fyd if fyd is not None else fy / gamma_s

        # 항복변형률
        self.esy = self.fyd / Es

    # ──────────────────────────────────────────────────────────────────
    def stress(self, strain: float) -> float:
        """
        Args:
            strain: 변형률 (압축 = +, 인장 = -)
        Returns:
            응력 [MPa] (압축 = +, 인장 = -)
        """
        if self.curve_type == self.BLH:
            return self._bilinear_hardening(strain)
        return self._elastic_perfectly_plastic(strain)

    def elastic_modulus(self) -> float:
        return self.Es

    @property
    def label(self) -> str:
        return f"Rebar fy={self.fy:.0f} MPa (fyd={self.fyd:.1f})"

    # ──────────────────────────────────────────────────────────────────
    def _elastic_perfectly_plastic(self, eps: float) -> float:
        """완전 탄소성 (Elastic-Perfectly Plastic)"""
        sign = np.sign(eps) if eps != 0.0 else 0.0
        if abs(eps) <= self.esy:
            return self.Es * eps
        elif abs(eps) <= self.esu:
            return sign * self.fyd
        else:
            return sign * self.fyd  # 파단 이후도 항복강도 유지 (보수적)

    def _bilinear_hardening(self, eps: float) -> float:
        """변형경화 포함 이선형 (Bilinear with Strain Hardening)"""
        sign = np.sign(eps) if eps != 0.0 else 0.0
        abs_eps = abs(eps)
        if abs_eps <= self.esy:
            return self.Es * eps
        elif abs_eps <= self.esu:
            sigma_y = self.fyd
            E_h = self.Es * self.hardening_ratio
            return sign * (sigma_y + E_h * (abs_eps - self.esy))
        else:
            return sign * self.fyd  # 파단 이후

    def __repr__(self) -> str:
        return (
            f"Rebar(fy={self.fy}, fyd={self.fyd:.2f}, "
            f"Es={self.Es:.0f}, εsy={self.esy*1e3:.3f}‰)"
        )
