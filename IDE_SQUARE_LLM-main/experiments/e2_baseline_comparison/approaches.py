"""
Three approaches for state machine generation comparison.

B1: SingleLLMApproach - Direct LLM generation without Square logic
B2: ManualSquareApproach - Pure rule-based heuristics (NO LLM, NO bot)
S:  SquareBotApproach - Full MAS-LLM agent pipeline
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.llm_agent import LLMAgent
from src.agents.logic_agent import LogicAgent
from src.agents.state_agent import StateAgent
from src.agents.verifier_agent import VerifierAgent

from .heuristics import (
    STATE_KEYWORDS, 
    LIFECYCLE_ORDER, 
    is_initial_state, 
    is_final_state,
    get_lifecycle_order,
)


class SingleLLMApproach:
    """
    B1: Single-LLM prompt approach.
    
    Uses a single LLM call without Square of Opposition logic
    to generate state machine directly from requirements.
    
    Pros: Simple, fast
    Cons: No logical validation, prone to hallucination
    """
    
    def __init__(self):
        self.llm_agent = LLMAgent()
        self.max_iterations = 1  # Single shot, no refinement
    
    async def generate(self, requirements: str) -> Tuple[Dict[str, Any], int]:
        """
        Generate state machine from requirements using single LLM prompt.
        
        Returns:
            Tuple of (state_machine_dict, iterations)
        """
        prompt = f"""
Analyze the following requirements and generate a state machine model directly.

Requirements:
{requirements}

Generate a complete state machine with:
1. All states (with name, description, is_initial, is_final flags)
2. All transitions (from_state, to_state, condition, action)

IMPORTANT: Only create states that represent actual lifecycle stages.
Do NOT include attribute-like concepts as states.

Respond with a JSON object:
{{
    "states": [
        {{"name": "state_name", "description": "...", "is_initial": true/false, "is_final": true/false}}
    ],
    "transitions": [
        {{"from_state": "state1", "to_state": "state2", "condition": "...", "action": "..."}}
    ],
    "initial_state": "initial_state_name"
}}
"""
        
        try:
            # Note: LLMAgent uses synchronous OpenAI client
            response = self.llm_agent.client.chat.completions.create(
                model=self.llm_agent.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON from response
            json_text = self._extract_json(result_text)
            state_machine = json.loads(json_text)
            
            # Validate structure
            if "states" not in state_machine:
                state_machine["states"] = []
            if "transitions" not in state_machine:
                state_machine["transitions"] = []
                
            return state_machine, 1
            
        except json.JSONDecodeError as e:
            return {
                "states": [], 
                "transitions": [], 
                "error": f"JSON parse error: {str(e)}"
            }, 1
        except Exception as e:
            return {"states": [], "transitions": [], "error": str(e)}, 1
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response text."""
        # Method 1: Extract from ```json blocks
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                return parts[1].strip()
        
        # Method 2: Find JSON object directly
        if not text.strip().startswith("{"):
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                return text[start_idx:end_idx]
        
        return text


class ManualSquareApproach:
    """
    B2: Manual Square logic approach (NO LLM, NO bot).
    
    Uses ONLY rule-based heuristics to extract states from requirements
    and applies Square of Opposition logic manually.
    Iterates until model stabilizes (no more contradictions to resolve).
    
    Pros: Deterministic, fast, no API calls
    Cons: Limited by hardcoded keywords, no semantic understanding
    """
    
    def __init__(self):
        self.max_iterations = 5
    
    async def generate(self, requirements: str) -> Tuple[Dict[str, Any], int]:
        """
        Generate state machine using only manual heuristics.
        No LLM calls - purely rule-based with iterative refinement.
        
        Returns:
            Tuple of (state_machine_dict, iterations)
        """
        iterations = 0
        previous_state_count = -1
        states = []
        state_names = set()
        
        # Iterative refinement loop
        while iterations < self.max_iterations:
            iterations += 1
            
            # Step 1: Extract states using keyword matching
            states, state_names = self._extract_states_from_keywords(requirements)
            
            # Step 2: Apply Square of Opposition rules to validate state pairs
            states, removed_count = self._apply_square_validation(states)
            state_names = {s["name"] for s in states}
            
            # Step 3: Check for stability (no more changes)
            current_state_count = len(states)
            if current_state_count == previous_state_count and removed_count == 0:
                break
            previous_state_count = current_state_count
            
            # Step 4: If contradictions were removed, refine transitions
            if removed_count > 0:
                # Need another iteration to stabilize
                continue
            else:
                # No more contradictions - stable
                break
        
        # Generate transitions using lifecycle ordering
        transitions = self._generate_transitions(state_names)
        
        state_machine = {
            "states": states,
            "transitions": transitions,
            "initial_state": next((s["name"] for s in states if s.get("is_initial")), None)
        }
        
        return state_machine, iterations
    
    def _extract_states_from_keywords(self, requirements: str) -> Tuple[List[Dict[str, Any]], set]:
        """Extract states by matching keywords in requirements text."""
        states = []
        state_names = set()
        req_lower = requirements.lower()
        
        for keyword in STATE_KEYWORDS:
            if keyword in req_lower and keyword not in state_names:
                state_names.add(keyword)
                states.append({
                    "name": keyword,
                    "description": f"State extracted from requirements",
                    "is_initial": is_initial_state(keyword),
                    "is_final": is_final_state(keyword)
                })
        
        return states, state_names
    
    def _apply_square_validation(self, states: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Apply Square of Opposition rules to validate states.
        Returns validated states and count of removed contradictions.
        
        Contradictory pairs (cannot both exist - keep only one):
        - active/inactive
        - open/closed  
        - valid/invalid
        - approved/rejected
        """
        contradictory_pairs = [
            ("active", "inactive"),
            ("open", "closed"),
            ("valid", "invalid"),
            ("approved", "rejected"),
            ("enabled", "disabled"),
            ("confirmed", "cancelled"),
            ("authorized", "declined"),
            ("in_stock", "out_of_stock"),
        ]
        
        state_names = {s["name"] for s in states}
        validated = []
        removed_count = 0
        to_remove = set()
        
        # Find contradictory pairs and mark one for removal
        for a, b in contradictory_pairs:
            if a in state_names and b in state_names:
                # Both exist - remove the "negative" one (second in pair)
                to_remove.add(b)
                removed_count += 1
        
        # Keep only non-contradictory states
        for state in states:
            if state["name"] not in to_remove:
                validated.append(state)
        
        return validated, removed_count
    
    def _generate_transitions(self, state_names: set) -> List[Dict[str, Any]]:
        """Generate transitions using lifecycle ordering heuristics."""
        transitions = []
        
        # Sort by lifecycle order
        sorted_states = sorted(state_names, key=get_lifecycle_order)
        
        # Connect sequential states
        for i in range(len(sorted_states) - 1):
            from_state = sorted_states[i]
            to_state = sorted_states[i + 1]
            
            if not is_final_state(from_state):
                transitions.append({
                    "from_state": from_state,
                    "to_state": to_state,
                    "condition": f"transition_to_{to_state}",
                    "action": f"move_to_{to_state}"
                })
        
        # Add cancellation transitions to cancelled state if exists
        if "cancelled" in state_names:
            for state in sorted_states:
                if state != "cancelled" and not is_final_state(state):
                    transitions.append({
                        "from_state": state,
                        "to_state": "cancelled",
                        "condition": "cancel_requested",
                        "action": "cancel"
                    })
        
        return transitions


class SquareBotApproach:
    """
    S: Full Square-driven bot approach.
    
    Uses the complete MAS-LLM pipeline with all agents:
    LLMAgent -> LogicAgent -> StateAgent -> VerifierAgent
    with iterative refinement until stable.
    
    Pros: Full logical validation, intelligent refinement
    Cons: More complex, slower
    """
    
    def __init__(self):
        self.max_iterations = 5
    
    async def generate(self, requirements: str) -> Tuple[Dict[str, Any], int]:
        """
        Generate state machine using full agent pipeline.
        
        Returns:
            Tuple of (state_machine_dict, iterations)
        """
        iterations = 0
        previous_states = None
        current_state_machine = {"states": [], "transitions": []}
        
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # 1. LLM Agent - Extract requirements
                llm_agent = LLMAgent()
                llm_result = await llm_agent.execute({
                    "task_type": "extract_requirements",
                    "user_input": requirements
                })
                
                if not llm_result.get("success"):
                    break
                
                extracted_reqs = llm_result["result"]["requirements"]
                
                # 2. Logic Agent - Build logic model
                logic_agent = LogicAgent()
                logic_result = await logic_agent.execute({
                    "requirements": extracted_reqs
                })
                
                if not logic_result.get("success"):
                    break
                
                logic_model = logic_result["result"].get("logic_model", {})
                
                # 3. State Agent - Generate state machine
                state_agent = StateAgent()
                state_agent.set_llm_agent(llm_agent)
                
                state_result = await state_agent.execute({
                    "logic_model": logic_model,
                    "requirements": extracted_reqs
                })
                
                if not state_result.get("success"):
                    break
                
                current_state_machine = state_result["result"].get("state_machine", {})
                
                # 4. Check for stability
                current_states = set(
                    s.get("name", "") for s in current_state_machine.get("states", [])
                )
                
                if previous_states == current_states:
                    break
                
                previous_states = current_states
                
                # 5. Verify and potentially refine
                verifier_agent = VerifierAgent()
                verify_result = await verifier_agent.execute({
                    "requirements": extracted_reqs,
                    "logic_model": logic_model,
                    "state_machine": current_state_machine,
                })
                
                if verify_result.get("is_consistent", True):
                    break
                    
            except Exception as e:
                current_state_machine["error"] = str(e)
                break
        
        return current_state_machine, iterations
