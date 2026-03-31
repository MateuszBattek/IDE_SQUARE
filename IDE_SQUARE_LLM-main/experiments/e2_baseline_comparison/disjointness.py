"""
Disjointness verification for state machines.

Checks if states are mutually exclusive and transitions are deterministic.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class DisjointnessResult:
    """Result of disjointness verification."""
    passed: bool
    violations: List[str] = field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
        }


def check_disjointness(state_machine: Dict[str, Any]) -> DisjointnessResult:
    """
    Check if states in the state machine are disjoint (mutually exclusive).
    
    Performs 5 checks:
    1. No duplicate state names
    2. No self-loops in transitions
    3. No conflicting transitions (same from_state + condition → different to_states)
    4. All transitions reference valid states
    5. No semantically overlapping state names
    
    Args:
        state_machine: State machine dict with 'states' and 'transitions'
        
    Returns:
        DisjointnessResult with pass/fail and violation details
    """
    states = state_machine.get("states", [])
    transitions = state_machine.get("transitions", [])
    
    violations = []
    total_checks = 0
    passed_checks = 0
    
    # Check 1: No duplicate state names
    total_checks += 1
    state_names = [s.get("name", "").lower() for s in states]
    unique_names = set(state_names)
    if len(state_names) != len(unique_names):
        violations.append("Duplicate state names detected")
    else:
        passed_checks += 1
    
    # Check 2: No self-loops
    total_checks += 1
    self_loops = [t for t in transitions if t.get("from_state") == t.get("to_state")]
    if self_loops:
        violations.append(f"Self-loop transitions detected: {len(self_loops)}")
    else:
        passed_checks += 1
    
    # Check 3: No conflicting transitions
    total_checks += 1
    transition_map: Dict[str, List[str]] = {}
    for t in transitions:
        key = f"{t.get('from_state', '')}:{t.get('condition', 'default')}"
        if key not in transition_map:
            transition_map[key] = []
        transition_map[key].append(t.get("to_state", ""))
    
    conflicting = {k: v for k, v in transition_map.items() if len(set(v)) > 1}
    if conflicting:
        violations.append(f"Conflicting transitions detected: {len(conflicting)}")
    else:
        passed_checks += 1
    
    # Check 4: All transitions reference valid states
    total_checks += 1
    valid_state_names = set(s.get("name", "") for s in states)
    invalid_refs = []
    for t in transitions:
        if t.get("from_state", "") not in valid_state_names:
            invalid_refs.append(t.get("from_state", ""))
        if t.get("to_state", "") not in valid_state_names:
            invalid_refs.append(t.get("to_state", ""))
    
    if invalid_refs:
        violations.append(f"Transitions reference invalid states: {set(invalid_refs)}")
    else:
        passed_checks += 1
    
    # Check 5: Semantic disjointness
    total_checks += 1
    semantically_similar = []
    for i, name1 in enumerate(state_names):
        for name2 in state_names[i+1:]:
            if name1 and name2 and (name1 in name2 or name2 in name1):
                semantically_similar.append((name1, name2))
    
    if semantically_similar:
        violations.append(f"Semantically overlapping states: {semantically_similar}")
    else:
        passed_checks += 1
    
    return DisjointnessResult(
        passed=len(violations) == 0,
        violations=violations,
        total_checks=total_checks,
        passed_checks=passed_checks
    )
