"""
Eurocode 2 (EN 1992-1-1:2004) 설계기준

주요 조항:
  § 3.1.6  콘크리트 설계 강도  fcd = αcc · fck / γc
  § 3.1.3  탄성계수  Ecm = 22·(fcm/10)^0.3 ×10³  [GPa → MPa]
  § 3.1.9  응력-변형률 관계  εc1, εcu1, n
  § 2.4.2.4 재료계수
    - 영구·일시 조합:  γc = 1.5,  γs = 1.15
    - 극단(사고) 조합: γc = 1.2,  γs = 1.0

KDS와 동일한 포물선-직선형 응력-변형률 관계를 사용하나
재료계수(γc = 1.5)가 KDS(γc = 0.65)와 다릅니다.
"""
from .base import DesignCode, MaterialFactors


class EC2(DesignCode):
    """EN 1992-1-1:2004 Eurocode 2"""

    # ── 재료계수 ─────────────────────────────────────────────────────
    def material_factors(self, load_case: str = "ULS") -> MaterialFactors:
        """
        표 2.1N 재료계수

        "persistent"  (영구·일시): γc=1.5, γs=1.15, αcc=1.0
        "accidental"  (사고):      γc=1.2, γs=1.0,  αcc=1.0
        "SLS"         (사용):      γc=1.0, γs=1.0,  αcc=1.0
        """
        lc = load_case.upper()
        if lc in ("ACCIDENTAL", "ACC", "사고"):
            return MaterialFactors(gamma_c=1.2, gamma_s=1.0, alpha_cc=1.0)
        elif lc in ("SLS", "사용"):
            return MaterialFactors(gamma_c=1.0, gamma_s=1.0, alpha_cc=1.0)
        else:  # ULS persistent (기본)
            return MaterialFactors(gamma_c=1.5, gamma_s=1.15, alpha_cc=1.0)

    # ── 콘크리트 ─────────────────────────────────────────────────────
    def fcd(self, fck: float, load_case: str = "ULS") -> float:
        """식 (3.15):  fcd = αcc · fck / γc"""
        mf = self.material_factors(load_case)
        return mf.alpha_cc * fck / mf.gamma_c

    def epsilon_cu(self, fck: float) -> float:
        """표 3.1:  εcu1 (EC2 기호 εcu1 = εcu in KDS)"""
        if fck <= 50.0:
            return 3.5e-3
        x = (90.0 - fck) / 100.0
        return (2.6 + 35.0 * x ** 4) * 1e-3

    def epsilon_c1(self, fck: float) -> float:
        """표 3.1: εc1 (정점변형률)"""
        if fck <= 50.0:
            return 2.0e-3
        return (2.0 + 0.085 * (fck - 50.0) ** 0.53) * 1e-3

    def stress_block_n(self, fck: float) -> float:
        """표 3.1: 포물선 지수 n"""
        if fck <= 50.0:
            return 2.0
        x = (90.0 - fck) / 100.0
        return 1.4 + 23.4 * x ** 4

    def elastic_modulus_concrete(self, fck: float) -> float:
        """
        식 (3.5):  Ecm = 22·(fcm/10)^0.3 ×10³  [MPa]
        fcm = fck + 8  (표 3.1, fck ≤ 50 기준)
        """
        fcm = fck + (8.0 if fck <= 50.0 else 4.0)
        return 22.0 * (fcm / 10.0) ** 0.3 * 1_000.0

    # ── 철근/강연선 ───────────────────────────────────────────────────
    def fyd(self, fy: float, load_case: str = "ULS") -> float:
        """식 (3.6):  fyd = fyk / γs"""
        mf = self.material_factors(load_case)
        return fy / mf.gamma_s

    def fpd(self, fp01k: float, load_case: str = "ULS") -> float:
        """강연선:  fpd = fp0.1k / γs"""
        mf = self.material_factors(load_case)
        return fp01k / mf.gamma_s

    # ── 강도감소계수 ─────────────────────────────────────────────────
    def phi_factor(self, et: float = 0.0, section_type: str = "tied") -> float:
        """EC2는 재료계수 방식 → 추가 강도감소계수 = 1.0"""
        return 1.0

    # ── 공통 ─────────────────────────────────────────────────────────
    @property
    def code_name(self) -> str:
        return "EN 1992-1-1:2004 (Eurocode 2)"

    def summary(self) -> str:
        return (
            "【Eurocode 2 (EN 1992-1-1)】\n"
            "  ULS 재료계수: γc = 1.5,  γs = 1.15\n"
            "  fcd = αcc·fck / γc  (αcc = 1.0)\n"
            "  fyd = fyk / γs\n"
            "  εcu = 3.5‰ (fck ≤ 50 MPa)\n"
            "  φ = 1.0 (재료계수에 내포)"
        )
