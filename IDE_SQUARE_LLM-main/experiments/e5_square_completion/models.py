"""
Data classes for E5 Square Completion experiment results.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class CornerType(str, Enum):
    """Square of Opposition corner types."""
    A = "universal_affirmative"
    E = "universal_negative"
    I = "particular_affirmative"
    O = "particular_negative"


class ScenarioType(str, Enum):
    """Types of corner scenarios being tested."""
    C1_ONE_CORNER = "C1_one_corner"
    C2_TWO_CORNERS = "C2_two_corners"
    C3_THREE_CORNERS = "C3_three_corners"


@dataclass
class SquareRelation:
    """A single Square of Opposition relation."""
    corner: CornerType
    subject: str
    predicate: str
    status: str  # TRUE, FALSE, UNDETERMINED
    statement: str = ""
    natural_language: str = ""


@dataclass
class E5InferenceResult:
    """Result of a single square completion inference."""
    scenario_type: ScenarioType
    test_case_name: str
    given_corners: List[CornerType]
    expected_inferences: Dict[str, SquareRelation]  # corner -> relation
    actual_inferences: Dict[str, SquareRelation]
    
    # Accuracy metrics
    correct_relations: int = 0
    total_relations: int = 0
    correct_statuses: int = 0
    
    execution_time: float = 0.0
    error: Optional[str] = None


@dataclass 
class E5ScenarioResult:
    """Aggregated results for a scenario type (C1, C2, or C3)."""
    scenario_type: ScenarioType
    test_cases: List[E5InferenceResult]
    
    # Aggregated metrics
    avg_relation_accuracy: float = 0.0
    avg_status_accuracy: float = 0.0
    total_correct: int = 0
    total_inferences: int = 0


@dataclass
class E5StateMachineImpact:
    """Impact of corner input on state machine generation."""
    scenario_type: ScenarioType
    f1_with_completion: float  # F1 when using inferred relations
    f1_without_completion: float  # F1 with only given relations
    f1_improvement: float  # Difference


@dataclass
class E5ExperimentSummary:
    """Summary of the entire E5 experiment."""
    scenario_results: Dict[ScenarioType, E5ScenarioResult]
    sm_impact: Dict[ScenarioType, E5StateMachineImpact]
    
    # Overall accuracy by number of corners
    accuracy_by_corners: Dict[int, float]  # 1, 2, 3 -> accuracy
    
    timestamp: str
