"""
Reference model loading and comparison utilities.

Handles loading reference models and noise variants from JSON files
for E1 and E3 experiments.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class NoiseLevel(str, Enum):
    """Noise levels for E3 experiment."""
    CLEAN = "clean"
    SLIGHT = "slight"
    HEAVY = "heavy"


@dataclass
class ReferenceModel:
    """Reference model for evaluation."""
    name: str
    description: str
    requirements: str
    expected_states: List[Dict[str, Any]]
    expected_transitions: List[Dict[str, Any]]
    expected_entities: List[str] = field(default_factory=list)
    expected_relations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_state_machine_dict(self) -> Dict[str, Any]:
        """Convert to state machine dictionary format."""
        return {
            "states": self.expected_states,
            "transitions": self.expected_transitions,
            "initial_state": next(
                (s["name"] for s in self.expected_states if s.get("is_initial")),
                self.expected_states[0]["name"] if self.expected_states else None
            ),
            "metadata": {"reference_model": self.name}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReferenceModel":
        """Create ReferenceModel from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            requirements=data["requirements"],
            expected_states=data["expected_states"],
            expected_transitions=data["expected_transitions"],
            expected_entities=data.get("expected_entities", []),
            expected_relations=data.get("expected_relations", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class NoiseVariant:
    """A requirements variant with specific noise level."""
    name: str
    noise_level: NoiseLevel
    requirements: str
    description: str = ""
    noise_description: str = ""  # What type of noise was applied
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NoiseVariant":
        """Create NoiseVariant from dictionary."""
        return cls(
            name=data["name"],
            noise_level=NoiseLevel(data["noise_level"]),
            requirements=data["requirements"],
            description=data.get("description", ""),
            noise_description=data.get("noise_description", ""),
        )


@dataclass
class NoiseTestCase:
    """Complete test case with all noise variants."""
    name: str
    reference_model: ReferenceModel
    variants: Dict[NoiseLevel, NoiseVariant]
    
    def get_clean(self) -> NoiseVariant:
        return self.variants[NoiseLevel.CLEAN]
    
    def get_slight(self) -> NoiseVariant:
        return self.variants[NoiseLevel.SLIGHT]
    
    def get_heavy(self) -> NoiseVariant:
        return self.variants[NoiseLevel.HEAVY]


def get_default_data_dir() -> Path:
    """Get default test data directory."""
    # Navigate from src/evaluation to experiments/test_data
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "experiments" / "test_data"


def load_reference_models(
    file_path: Optional[Path] = None
) -> List[ReferenceModel]:
    """
    Load reference models from JSON file.
    
    Args:
        file_path: Path to JSON file. If None, uses default location.
        
    Returns:
        List of ReferenceModel objects
    """
    if file_path is None:
        file_path = get_default_data_dir() / "e1_reference_models.json"
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    models = []
    for model_data in data.get("reference_models", []):
        models.append(ReferenceModel.from_dict(model_data))
    
    return models


def load_noise_variants(
    file_path: Optional[Path] = None
) -> List[NoiseTestCase]:
    """
    Load noise variants from JSON file for E3 experiment.
    
    Args:
        file_path: Path to JSON file. If None, uses default location.
        
    Returns:
        List of NoiseTestCase objects with all variants
    """
    if file_path is None:
        file_path = get_default_data_dir() / "e3_noise_variants.json"
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    test_cases = []
    for case_data in data.get("test_cases", []):
        # Load reference model
        ref_model = ReferenceModel.from_dict(case_data["reference_model"])
        
        # Load variants
        variants = {}
        for variant_data in case_data.get("variants", []):
            variant = NoiseVariant.from_dict(variant_data)
            variants[variant.noise_level] = variant
        
        test_cases.append(NoiseTestCase(
            name=case_data["name"],
            reference_model=ref_model,
            variants=variants,
        ))
    
    return test_cases


def compare_with_reference(
    generated: Dict[str, Any],
    reference: ReferenceModel
) -> Dict[str, Any]:
    """
    Quick comparison of generated model with reference.
    
    Returns dict with match statistics without full metric calculation.
    """
    from .metrics import (
        _extract_state_names_from_dict,
        _extract_transitions_from_dict,
        _normalize_name,
    )
    
    gen_states = _extract_state_names_from_dict(generated)
    ref_states = {_normalize_name(s["name"]) for s in reference.expected_states}
    
    gen_trans = _extract_transitions_from_dict(generated)
    ref_trans = {
        (_normalize_name(t.get("from_state", t.get("from", ""))),
         _normalize_name(t.get("to_state", t.get("to", ""))))
        for t in reference.expected_transitions
    }
    
    matched_states = gen_states & ref_states
    matched_trans = gen_trans & ref_trans
    
    extra_states = gen_states - ref_states
    missing_states = ref_states - gen_states
    extra_trans = gen_trans - ref_trans
    missing_trans = ref_trans - gen_trans
    
    return {
        "matched_states": list(matched_states),
        "matched_transitions": [list(t) for t in matched_trans],
        "extra_states": list(extra_states),
        "missing_states": list(missing_states),
        "extra_transitions": [list(t) for t in extra_trans],
        "missing_transitions": [list(t) for t in missing_trans],
        "state_match_rate": len(matched_states) / len(ref_states) if ref_states else 1.0,
        "transition_match_rate": len(matched_trans) / len(ref_trans) if ref_trans else 1.0,
    }
