"""
KDS 24 14 21:2025 콘크리트교 설계기준 (한계상태설계법)

주요 근거 조항:
  § 1.4  재료계수  표 1.4-1
    - 극한한계상태:  γc = 0.65,  γs = 0.9
    - 사용/피로:     γc = 1.0,   γs = 1.0
  § 3.1.2.6  설계압축강도   fcd = αcc · fck · γc   (αcc=0.85, γc=0.65)
  § 3.1.2.1  평균압축강도   fcm = fck + Δf          식 (3.1-1)
  § 3.1.2.2  탄성계수       Ecm = 22(fcm/10)^0.3·10³ 식 (3.1-10)
  § 3.1 표 3.1-2  비선형 해석 변형률 파라미터 εco,r / εcu,r
"""
from .base import DesignCode, MaterialFactors

# ── 표 3.1-2: 비선형 해석을 위한 콘크리트 응력-변형률 계수 ─────────────
# fck  [MPa]
_T312_FCK  = [18,   21,   24,   27,   30,   35,   40,   50,   60,   70,   80,   90  ]
# εco,r [‰]  (정점변형률, 비선형 해석용)
_T312_ECOR = [1.85, 1.90, 1.97, 2.03, 2.09, 2.18, 2.26, 2.42, 2.57, 2.60, 2.79, 2.80]
# εcu,r [‰]  (극한변형률, 비선형 해석용)
_T312_ECUR = [3.3,  3.3,  3.3,  3.3,  3.3,  3.3,  3.3,  3.2,  3.1,  3.0,  2.9,  2.8 ]


def _interp_t312(fck: float, y_table) -> float:
    """표 3.1-2 선형 보간 (범위 밖은 경계값)"""
    xt = _T312_FCK; yt = y_table
    if fck <= xt[0]:  return yt[0]
    if fck >= xt[-1]: return yt[-1]
    for i in range(len(xt) - 1):
        if xt[i] <= fck <= xt[i + 1]:
            t = (fck - xt[i]) / (xt[i + 1] - xt[i])
            return yt[i] + t * (yt[i + 1] - yt[i])
    return yt[-1]


class KDS241421(DesignCode):
    """KDS 24 14 21:2025 한계상태설계법"""

    # ── 재료계수 ─────────────────────────────────────────────────────
    # KDS 24 14 21 표 1.4-1:
    #   γc = 0.65, γs = 0.9 (재료계수 방식 — 곱하기, KDS 표 1.4-1 극한한계상태)
    #   αcc = 0.85 (콘크리트 압축강도 유효계수, § 3.1.2.6)
    #   fcd = αcc × fck × γc = 0.85 × fck × 0.65 = 0.5525 × fck
    #   fyd = fy  × γs  = fy  × 0.9
    # ※ EC2 방식(나누기, γc=1.5)과 다름을 주의
    def material_factors(self, load_case: str = "ULS") -> MaterialFactors:
        if load_case.upper() in ("ULS", "극한"):
            return MaterialFactors(gamma_c=0.65, gamma_s=0.9, alpha_cc=0.85)
        else:  # SLS, fatigue
            return MaterialFactors(gamma_c=1.0, gamma_s=1.0, alpha_cc=1.0)

    # ── 콘크리트 ─────────────────────────────────────────────────────
    def fcd(self, fck: float, load_case: str = "ULS") -> float:
        """
        fcd = αcc · fck · γc  (KDS § 3.1.2.6, 표 1.4-1)
        αcc = 0.85 (콘크리트 압축강도 유효계수), γc = 0.65 (ULS)
        → fcd = 0.85 × 0.65 × fck = 0.5525 · fck
        """
        mf = self.material_factors(load_case)
        return mf.alpha_cc * fck * mf.gamma_c   # ← 곱하기 (not 나누기)

    def epsilon_cu(self, fck: float) -> float:
        """극한압축변형률 εcu,r  (표 3.1-2, 비선형 해석용 보간)"""
        return _interp_t312(fck, _T312_ECUR) * 1e-3

    def epsilon_c1(self, fck: float) -> float:
        """정점변형률 εco,r  (표 3.1-2, 비선형 해석용 보간)"""
        return _interp_t312(fck, _T312_ECOR) * 1e-3

    def stress_block_n(self, fck: float) -> float:
        """포물선 지수 n  (표 3.1-1 / 식 3.1-42)"""
        if fck <= 50.0:
            return 2.0
        x = (90.0 - fck) / 100.0
        return 1.4 + 23.4 * x ** 4

    def elastic_modulus_concrete(self, fck: float) -> float:
        """
        식 (3.1-10):  Ecm = 22 × (fcm/10)^0.3 × 10³  [MPa]
        """
        fcm = fck + (8.0 if fck <= 50.0 else 4.0)
        return 22.0 * (fcm / 10.0) ** 0.3 * 1_000.0

    # ── 철근/강연선 ───────────────────────────────────────────────────
    def fyd(self, fy: float, load_case: str = "ULS") -> float:
        """설계항복강도  fyd = fy · γs  (γs=0.9 → fyd = 0.9·fy)"""
        mf = self.material_factors(load_case)
        return fy * mf.gamma_s   # ← 곱하기: γs=0.9

    def fpd(self, fp01k: float, load_case: str = "ULS") -> float:
        """강연선 설계항복강도  fpd = fp01k · γs"""
        mf = self.material_factors(load_case)
        return fp01k * mf.gamma_s

    # ── 강도감소계수 ─────────────────────────────────────────────────
    def phi_factor(self, et: float = 0.0, section_type: str = "tied") -> float:
        """
        KDS 한계상태설계법에서는 재료계수(γc, γs)로 강도 감소를 수행합니다.
        → 추가 강도감소계수 φ = 1.0
        """
        return 1.0

    # ── 공통 ─────────────────────────────────────────────────────────
    @property
    def code_name(self) -> str:
        return "KDS 24 14 21:2025 (한계상태설계법)"

    def summary(self) -> str:
        """기준 핵심 파라미터 요약"""
        return (
            "【KDS 24 14 21:2025】\n"
            "  ULS 재료계수 (표 1.4-1): γc = 0.65,  γs = 0.9\n"
            "  αcc = 0.85  (콘크리트 압축강도 유효계수, § 3.1.2.6)\n"
            "  fcd = αcc·fck·γc  (= 0.85×0.65·fck = 0.5525·fck)\n"
            "  fyd = fy·γs       (= 0.9·fy)\n"
            "  εcu,r: 표 3.1-2 보간 (fck≤40→3.3‰, fck=90→2.8‰)\n"
            "  εco,r: 표 3.1-2 보간 (fck=30→2.09‰, ...)\n"
            "  Ecm = 22·(fcm/10)^0.3 ×10³ MPa\n"
            "  φ = 1.0 (재료계수에 내포)"
        )
