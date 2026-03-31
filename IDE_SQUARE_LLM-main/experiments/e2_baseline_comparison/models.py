"""
Data classes for E2 experiment results.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ApproachType(str, Enum):
    """Types of approaches being compared."""
    B1_SINGLE_LLM = "B1_single_llm"      # Single LLM prompt, no Square, no agents
    B2_MANUAL_SQUARE = "B2_manual_square" # Square logic manually, no bot
    S_SQUARE_BOT = "S_square_bot"         # Full Square-driven bot pipeline


@dataclass
class E2ApproachResult:
    """Result for a single approach on a single model."""
    approach: ApproachType
    model_name: str
    generated_machine: Dict[str, Any]  # {"states": [...], "transitions": [...]}
    iterations: int
    execution_time: float  # seconds
    error: Optional[str] = None


@dataclass
class E2ModelComparison:
    """Comparison of all approaches for a single model."""
    model_name: str
    description: str
    results: Dict[ApproachType, E2ApproachResult]
    metrics: Dict[ApproachType, Dict[str, Any]]


@dataclass
class E2ExperimentSummary:
    """Summary of the entire E2 experiment."""
    comparisons: List[E2ModelComparison]
    aggregate_metrics: Dict[ApproachType, Dict[str, float]]
    winner: ApproachType
    timestamp: str
