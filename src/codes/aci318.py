"""
ACI 318-19 설계기준

주요 조항:
  § 22.2.2  콘크리트 극한변형률    εcu = 0.003
  § 22.2.2  등가직사각형 응력블록  β1 = f(f'c)
  § 21.2.1  강도감소계수 φ
    - 순인장 지배: φ = 0.90 (tied) / 0.90 (spiral)
    - 압축 지배:   φ = 0.65 (tied) / 0.75 (spiral)
    - 전이 구간:   선형 보간  εt: 0.002 ~ 0.005

재료계수 방식: ACI는 공칭강도 × φ 방식 (재료계수 없음)
  - fcd = f'c  (재료계수 없이 공칭값 사용)
  - fyd = fy   (φ는 단면 수준에서 적용)
"""
from .base import DesignCode, MaterialFactors


class ACI318(DesignCode):
    """ACI 318-19 강도설계법"""

    # ── 재료계수 ─────────────────────────────────────────────────────
    def material_factors(self, load_case: str = "ULS") -> MaterialFactors:
        """ACI는 재료 수준 계수 없음 → γ = 1.0, φ는 단면 수준 별도 적용"""
        return MaterialFactors(gamma_c=1.0, gamma_s=1.0, alpha_cc=0.85)

    # ── 콘크리트 ─────────────────────────────────────────────────────
    def fcd(self, fck: float, load_case: str = "ULS") -> float:
        """
        ACI 공칭값 사용 (재료계수 없음)
        응력블록 강도: 0.85 f'c  는 별도 계산에서 처리
        """
        return fck   # f'c 그대로

    def epsilon_cu(self, fck: float) -> float:
        """§ 22.2.2.1: εcu = 0.003"""
        return 0.003

    def epsilon_c1(self, fck: float) -> float:
        """등가 응력블록 상한 기준 (β1·εcu에 대응)"""
        return 0.002

    def stress_block_n(self, fck: float) -> float:
        """ACI는 포물선 지수 대신 등가직사각형 블록 사용 → n=2 근사"""
        return 2.0

    def beta1(self, fck: float) -> float:
        """
        § 22.2.2.4.3  등가직사각형 응력블록 깊이 계수 β1

        fck ≤ 28 MPa : β1 = 0.85
        fck > 28 MPa : β1 = 0.85 − 0.05·(fck−28)/7,  최소 0.65
        """
        if fck <= 28.0:
            return 0.85
        return max(0.65, 0.85 - 0.05 * (fck - 28.0) / 7.0)

    def elastic_modulus_concrete(self, fck: float) -> float:
        """
        § 19.2.2.1  Ec = 4700·√f'c  [MPa]  (단위중량 2300 kg/m³ 가정)
        """
        return 4700.0 * fck ** 0.5

    # ── 철근/강연선 ───────────────────────────────────────────────────
    def fyd(self, fy: float, load_case: str = "ULS") -> float:
        """ACI: 공칭항복강도 그대로 사용"""
        return fy

    def fpd(self, fp01k: float, load_case: str = "ULS") -> float:
        """ACI: 공칭값 사용"""
        return fp01k

    # ── 강도감소계수 ─────────────────────────────────────────────────
    def phi_factor(self, et: float = 0.0, section_type: str = "tied") -> float:
        """
        § 21.2.2  강도감소계수 φ

        순인장 변형률 εt 기준:
          εt ≥ 0.005          : φ = 0.90 (인장 지배)
          εt ≤ εy (≈0.002)    : φ = 0.65 tied / 0.75 spiral (압축 지배)
          εy < εt < 0.005     : 선형 보간

        Args:
            et          : 최외단 인장철근 변형률 (양수 = 인장)
            section_type: "tied" 또는 "spiral"
        """
        phi_min = 0.75 if section_type == "spiral" else 0.65
        phi_max = 0.90
        et_min  = 0.002   # 압축 지배 한계 (≈ εy for fy=400)
        et_max  = 0.005   # 인장 지배 한계

        if et >= et_max:
            return phi_max
        elif et <= et_min:
            return phi_min
        else:
            # 선형 보간
            return phi_min + (phi_max - phi_min) * (et - et_min) / (et_max - et_min)

    # ── 공통 ─────────────────────────────────────────────────────────
    @property
    def code_name(self) -> str:
        return "ACI 318-19 (강도설계법)"

    def summary(self) -> str:
        return (
            "【ACI 318-19】\n"
            "  재료계수: 없음 (φ 방식)\n"
            "  εcu = 0.003\n"
            "  응력블록: 0.85f'c · β1·c\n"
            "  φ = 0.65~0.90 (tied, εt 기반)"
        )
