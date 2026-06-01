"""
설계기준 추상 인터페이스 (Abstract Design Code Interface)

KDS / ACI / Eurocode를 동일한 인터페이스로 교체할 수 있도록
추상 클래스(ABC) 구조로 설계되었습니다.

새 기준을 추가하려면:
    class MyCode(DesignCode):
        ... (추상 메서드 전체 구현)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict


@dataclass
class MaterialFactors:
    """재료계수 모음"""
    gamma_c: float   # 콘크리트 재료계수
    gamma_s: float   # 철근/강연선 재료계수
    alpha_cc: float  # 콘크리트 압축 유효계수


class DesignCode(ABC):
    """
    설계기준 추상 기반 클래스

    각 설계기준(KDS, ACI, EC2)은 이 클래스를 상속하여 구현합니다.
    """

    # ── 재료계수 ──────────────────────────────────────────────────────
    @abstractmethod
    def material_factors(self, load_case: str = "ULS") -> MaterialFactors:
        """
        하중조합에 따른 재료계수 반환

        Args:
            load_case: "ULS" (극한), "SLS" (사용), "fatigue" (피로)
        """

    # ── 콘크리트 ─────────────────────────────────────────────────────
    @abstractmethod
    def fcd(self, fck: float, load_case: str = "ULS") -> float:
        """콘크리트 설계압축강도 [MPa]"""

    @abstractmethod
    def epsilon_cu(self, fck: float) -> float:
        """콘크리트 극한압축변형률 εcu"""

    @abstractmethod
    def epsilon_c1(self, fck: float) -> float:
        """콘크리트 정점변형률 εc1"""

    @abstractmethod
    def stress_block_n(self, fck: float) -> float:
        """포물선 지수 n"""

    @abstractmethod
    def elastic_modulus_concrete(self, fck: float) -> float:
        """콘크리트 탄성계수 Ecm [MPa]"""

    # ── 철근/강연선 ───────────────────────────────────────────────────
    @abstractmethod
    def fyd(self, fy: float, load_case: str = "ULS") -> float:
        """철근 설계항복강도 [MPa]"""

    @abstractmethod
    def fpd(self, fp01k: float, load_case: str = "ULS") -> float:
        """강연선 설계항복강도 [MPa]"""

    # ── 강도감소계수 (ACI 방식) ────────────────────────────────────
    @abstractmethod
    def phi_factor(self, et: float, section_type: str = "tied") -> float:
        """
        강도감소계수 φ

        Args:
            et          : 최외단 인장 철근의 순 인장변형률
            section_type: "tied" | "spiral"

        Note:
            KDS(한계상태설계법)에서는 재료계수(γc, γs)로 강도가 이미 감소되어
            있으므로 φ = 1.0을 반환합니다.
        """

    # ── 공통 유틸 ────────────────────────────────────────────────────
    @property
    @abstractmethod
    def code_name(self) -> str:
        """설계기준 이름"""

    def __repr__(self) -> str:
        return f"DesignCode({self.code_name})"
