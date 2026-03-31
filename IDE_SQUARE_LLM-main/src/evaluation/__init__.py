"""
Evaluation module for MAS-LLM experiments.

Provides metrics for comparing generated state machines with reference models,
and utilities for loading/managing reference data.
"""

from .metrics import (
    calculate_f1_states,
    calculate_f1_transitions,
    calculate_proof_pass_percentage,
    calculate_graph_edit_distance,
    calculate_hallucination_rate,
    evaluate_model,
    EvaluationMetrics,
)

from .reference_models import (
    ReferenceModel,
    load_reference_models,
    load_noise_variants,
    compare_with_reference,
)

__all__ = [
    # Metrics
    "calculate_f1_states",
    "calculate_f1_transitions", 
    "calculate_proof_pass_percentage",
    "calculate_graph_edit_distance",
    "calculate_hallucination_rate",
    "evaluate_model",
    "EvaluationMetrics",
    # Reference models
    "ReferenceModel",
    "load_reference_models",
    "load_noise_variants",
    "compare_with_reference",
]
