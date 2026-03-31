"""
Data classes for E4 Algorithm Ablation experiment results.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class AblationVariant(str, Enum):
    """Types of ablation variants being tested."""
    V1_FULL = "V1_full_system"
    V2_NO_PROVER = "V2_no_prover"
    V3_NO_VERIFIER = "V3_no_verifier"
    V4_NO_SQUARE = "V4_no_square_completion"


@dataclass
class E4VariantResult:
    """Result for a single ablation variant on a single model."""
    variant: AblationVariant
    model_name: str
    generated_machine: Dict[str, Any]
    iterations: int
    execution_time: float  # seconds
    
    # Ablation-specific metrics
    contradictions_count: int = 0
    models_rejected: int = 0
    prover_calls: int = 0
    verifier_calls: int = 0
    
    error: Optional[str] = None


@dataclass
class E4StabilityResult:
    """Stability test result (3 runs per variant)."""
    variant: AblationVariant
    model_name: str
    f1_scores: List[float]  # F1 from each run
    f1_mean: float
    f1_std: float  # Standard deviation
    is_stable: bool  # std <= 0.05


@dataclass
class E4ModelComparison:
    """Comparison of all variants for a single model."""
    model_name: str
    description: str
    results: Dict[AblationVariant, E4VariantResult]
    stability: Dict[AblationVariant, E4StabilityResult]
    metrics: Dict[AblationVariant, Dict[str, Any]]


@dataclass
class E4ExperimentSummary:
    """Summary of the entire E4 ablation experiment."""
    comparisons: List[E4ModelComparison]
    aggregate_metrics: Dict[AblationVariant, Dict[str, float]]
    component_impact: Dict[str, float]  # Impact of each component
    timestamp: str
