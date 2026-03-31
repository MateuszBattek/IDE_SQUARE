"""
E2 Experiment: Baseline vs Square-Bot Comparison

This experiment compares three approaches:
- B1: Single-LLM prompt (no Square logic, no agents)
- B2: Square logic manually applied (no bot, rule-based)
- S: Square-driven bot (full MAS-LLM pipeline)

Metrics measured:
- F1_states: F1 score for state matching
- Disjointness_pass: Pass/fail for state disjointness verification
- Iterations_to_stable: Number of iterations until model stabilizes

Usage:
    python -m experiments.e2_baseline_comparison [--model MODEL_NAME] [--verbose]
"""

from .main import run_e2_experiment
from .approaches import SingleLLMApproach, ManualSquareApproach, SquareBotApproach
from .disjointness import check_disjointness, DisjointnessResult

__all__ = [
    "run_e2_experiment",
    "SingleLLMApproach", 
    "ManualSquareApproach",
    "SquareBotApproach",
    "check_disjointness",
    "DisjointnessResult",
]
