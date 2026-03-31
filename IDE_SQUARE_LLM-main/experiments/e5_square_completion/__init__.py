"""
E5 Experiment: Square Completion Accuracy

This experiment tests the accuracy of Square of Opposition completion
when given partial input (1, 2, or 3 corners).

Scenarios:
- C1 (1 corner): Only A, E, I, or O given
- C2 (2 corners): Two corners given (e.g., A+E, I+O)
- C3 (3 corners): Three corners given

Metrics:
- correct_relations: % of correctly inferred relations
- status_accuracy: % of correct TRUE/FALSE/UNDETERMINED statuses
- sm_f1_impact: Impact on state machine F1 score

Usage:
    python -m experiments.e5_square_completion [--scenario SCENARIO] [--verbose]
"""

from .main import run_e5_experiment
from .corner_scenarios import (
    OneCornerScenario,
    TwoCornerScenario,
    ThreeCornerScenario,
    SquareTestCase,
)

__all__ = [
    "run_e5_experiment",
    "OneCornerScenario",
    "TwoCornerScenario",
    "ThreeCornerScenario",
    "SquareTestCase",
]
