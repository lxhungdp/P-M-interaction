from .base import DesignCode, MaterialFactors
from .kds2025 import KDS241421
from .aci318 import ACI318
from .ec2 import EC2

CODES = {
    "KDS 24 14 21:2025": KDS241421,
    "ACI 318-19":        ACI318,
    "Eurocode 2":        EC2,
}

__all__ = ["DesignCode", "MaterialFactors", "KDS241421", "ACI318", "EC2", "CODES"]
