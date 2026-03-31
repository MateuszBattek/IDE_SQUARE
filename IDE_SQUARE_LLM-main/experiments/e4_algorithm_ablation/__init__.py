"""
E4 Experiment: Algorithm Ablation Study

This experiment measures the contribution of each component (prover, verifier, 
square completion) to the overall system quality.

Variants:
- V1_FULL: Full system (baseline)
- V2_NO_PROVER: Without Z3 prover verification
- V3_NO_VERIFIER: Without consistency verifier
- V4_NO_SQUARE: Without square completion (LLM extraction only)

Metrics:
- contradictions_count: Number of contradictory states
- models_rejected: Number of models rejected by verifier
- stability_score: Variance of F1 across 3 runs (threshold ≤ 0.05)
- f1_states/f1_transitions: F1 scores vs reference

Usage:
    python -m experiments.e4_algorithm_ablation [--model MODEL_NAME] [--verbose]
"""

from .main import run_e4_experiment
from .variants import (
    FullSystemVariant,
    NoProverVariant,
    NoVerifierVariant,
    NoSquareCompletionVariant,
)

__all__ = [
    "run_e4_experiment",
    "FullSystemVariant",
    "NoProverVariant",
    "NoVerifierVariant",
    "NoSquareCompletionVariant",
]
