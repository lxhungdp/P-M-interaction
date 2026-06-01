"""
프리스트레싱 강연선(Strand) 재료 모델

KDS 24 14 21:2025 § 3.3 기반
핵심 특징: Locked-in prestrain(초기 긴장 변형률) 포함
응력 계산 시 기하학적 변형률 + 초기 긴장 변형률을 합산합니다.
"""
import numpy as np
from .base import Material


class Strand(Material):
    """
    프리스트레싱 강연선 재료 클래스

    지원 곡선 유형:
      - "bilinear"       : 이선형 (간략, 기본값)
      - "ramberg_osgood" : Ramberg-Osgood 근사 (부드러운 전이)

    초기 변형률(eps_pe):
      긴장 도입 후 콘크리트에 Lock-in된 강연선 변형률입니다.
      단면 해석 시  ε_eff = ε_geometric + eps_pe  로 적용됩니다.
    """

    BILINEAR = "bilinear"
    RAMBERG_OSGOOD = "ramberg_osgood"

    def __init__(
        self,
        fpk: float,
        fp01k: float,
        *,
        fpd: float = None,
        Ep: float = 195_000.0,
        gamma_s: float = 0.90,
        eps_pe: float = 0.0,
        epsu: float = 0.035,
        curve_type: str = "bilinear",
    ):
        """
        Args:
            fpk    : 기준인장강도  (characteristic tensile strength) [MPa]
            fp01k  : 기준항복강도  (0.1% 오프셋 항복강도) [MPa]
            fpd    : 설계항복강도  [MPa] ← 직접 지정 시 gamma_s 무시
            Ep     : 탄성계수 [MPa]  (KDS: 195,000 MPa)
            gamma_s: 강재 재료계수  (KDS ULS = 0.90)
            eps_pe : Locked-in prestrain (초기 긴장 변형률, 양수)
                     예) f_pe = 1,000 MPa → eps_pe = 1000 / 195000 ≈ 0.00513
            epsu   : 극한 변형률
            curve_type: 응력-변형률 곡선 유형
        """
        self.fpk = fpk
        self.fp01k = fp01k
        self.Ep = Ep
        self.gamma_s = gamma_s
        self.eps_pe = eps_pe         # ★ Locked-in prestrain
        self.epsu = epsu
        self.curve_type = curve_type

        # 설계항복강도  fpd = fp01k / γs
        self.fpd = fpd if fpd is not None else fp01k / gamma_s

        # 설계인장강도 (제한값)
        self.fptd = fpk / gamma_s

        # 탄성 한계 변형률
        self.epsy = self.fpd / Ep

    # ──────────────────────────────────────────────────────────────────
    def stress(self, geom_strain: float) -> float:
        """
        기하학적 변형률에서 응력 계산.
        실제 강연선에 작용하는 유효 변형률 = geom_strain + eps_pe

        Args:
            geom_strain: 단면 변형에 의한 기하학적 변형률 (압축 = +)
        Returns:
            응력 [MPa] (압축 = +)
        """
        eps_eff = geom_strain + self.eps_pe  # 프리스트레스 효과 합산

        if self.curve_type == self.RAMBERG_OSGOOD:
            return self._ramberg_osgood(eps_eff)
        return self._bilinear(eps_eff)

    def elastic_modulus(self) -> float:
        return self.Ep

    @property
    def label(self) -> str:
        return (
            f"Strand fpk={self.fpk:.0f} MPa "
            f"(fpd={self.fpd:.1f}, εpe={self.eps_pe*1e3:.2f}‰)"
        )

    # ──────────────────────────────────────────────────────────────────
    def _bilinear(self, eps: float) -> float:
        """이선형 탄소성 모델 (강연선 근사)"""
        sign = np.sign(eps) if eps != 0.0 else 0.0
        abs_eps = abs(eps)
        if abs_eps <= self.epsy:
            return self.Ep * eps
        elif abs_eps <= self.epsu:
            return sign * self.fpd
        else:
            return sign * self.fpd  # 파단 이후

    def _ramberg_osgood(self, eps: float) -> float:
        """
        Ramberg-Osgood 근사 (EN 1992-1-1 annex 참고)
        부드러운 항복 전이를 표현합니다.
        """
        sign = np.sign(eps) if eps != 0.0 else 0.0
        abs_eps = abs(eps)

        if abs_eps <= self.epsy:
            return self.Ep * eps

        # 수평선 근사 (간략화)
        if abs_eps <= self.epsu:
            # fpd 와 fpk 사이 부드러운 전이
            ratio = (abs_eps - self.epsy) / (self.epsu - self.epsy)
            sigma = self.fpd + (self.fptd - self.fpd) * ratio
            return sign * min(sigma, self.fptd)
        else:
            return sign * self.fptd

    # ──────────────────────────────────────────────────────────────────
    def effective_prestress(self) -> float:
        """유효 프리스트레스 응력  fpe = Ep × εpe  [MPa]"""
        return self.Ep * self.eps_pe

    def __repr__(self) -> str:
        return (
            f"Strand(fpk={self.fpk}, fpd={self.fpd:.2f}, "
            f"εpe={self.eps_pe*1e3:.3f}‰, Ep={self.Ep:.0f})"
        )
