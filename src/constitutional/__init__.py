"""
Constitutional AI — Three-Layer Framework.

Public surface:
  ThreeLayerFramework   — main evaluator (L1 + L2 + L3 simultaneously)
  ThreeLayerIntelligence — README-compatible alias
  ConstitutionalAI       — alias, same as ThreeLayerFramework
  MesaOptimizerCheck     — pre-execution mesa-optimizer pattern detector
  ConstitutionalViolation — exception raised on non-bypassable failures
  LayerResult            — result dataclass returned by each individual layer
"""

from .three_layer_framework import (
    ThreeLayerFramework,
    ThreeLayerIntelligence,
    FrameworkResult,
    ConstitutionalViolation,
    validate_framework,
)
from .mesa_optimizer_check import MesaOptimizerCheck, MesaCheckResult
from .l1_rational import L1RationalLayer, LayerResult
from .l2_empathic import L2EmpathicLayer
from .l3_social import L3SocialLayer

# Alias so code can import ConstitutionalAI directly
ConstitutionalAI = ThreeLayerFramework

__all__ = [
    "ThreeLayerFramework",
    "ThreeLayerIntelligence",
    "ConstitutionalAI",
    "FrameworkResult",
    "ConstitutionalViolation",
    "MesaOptimizerCheck",
    "MesaCheckResult",
    "L1RationalLayer",
    "L2EmpathicLayer",
    "L3SocialLayer",
    "LayerResult",
    "validate_framework",
]
