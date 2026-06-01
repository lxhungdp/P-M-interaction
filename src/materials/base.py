"""
재료 추상 기반 클래스
모든 재료(콘크리트, 철근, 강연선)는 이 클래스를 상속합니다.
"""
from abc import ABC, abstractmethod


class Material(ABC):
    """재료 추상 기반 클래스 (Abstract Base Class for all materials)"""

    @abstractmethod
    def stress(self, strain: float) -> float:
        """
        변형률로부터 응력을 계산합니다.

        Args:
            strain: 변형률 (압축 = +, 인장 = -)

        Returns:
            응력 [MPa] (압축 = +, 인장 = -)
        """

    @abstractmethod
    def elastic_modulus(self) -> float:
        """초기 탄성계수 E [MPa]"""

    @property
    @abstractmethod
    def label(self) -> str:
        """재료 표시 이름"""

    def tangent_modulus(self, strain: float, delta: float = 1e-7) -> float:
        """수치 미분으로 접선 탄성계수 계산 (비선형 해석용)"""
        return (self.stress(strain + delta) - self.stress(strain - delta)) / (2 * delta)
