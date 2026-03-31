"""
Ablation variants for E4 experiment.

Each variant represents a different configuration of the MAS-LLM pipeline
with specific components disabled for ablation study.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Tuple
from abc import ABC, abstractmethod

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.llm_agent import LLMAgent
from src.agents.logic_agent import LogicAgent
from src.agents.state_agent import StateAgent
from src.agents.verifier_agent import VerifierAgent
from src.agents.prover_agent import ProverAgent


class AblationVariant(ABC):
    """Base class for ablation variants."""
    
    def __init__(self):
        self.max_iterations = 5
        self.prover_calls = 0
        self.verifier_calls = 0
        self.contradictions_count = 0
        self.models_rejected = 0
    
    @abstractmethod
    async def generate(self, requirements: str) -> Tuple[Dict[str, Any], int]:
        """Generate state machine from requirements."""
        pass
    
    def get_metrics(self) -> Dict[str, int]:
        """Return ablation-specific metrics."""
        return {
            "prover_calls": self.prover_calls,
            "verifier_calls": self.verifier_calls,
            "contradictions_count": self.contradictions_count,
            "models_rejected": self.models_rejected,
        }


class FullSystemVariant(AblationVariant):
    """
    V1: Full system baseline.
    
    Uses complete MAS-LLM pipeline with all components:
    LLMAgent -> LogicAgent -> StateAgent -> VerifierAgent (with ProverAgent)
    """
    
    async def generate(self, requirements: str) -> Tuple[Dict[str, Any], int]:
        iterations = 0
        previous_states = None
        current_state_machine = {"states": [], "transitions": []}
        
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # 1. LLM Agent - Extract requirements with square completion
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
                
                # 5. Verify with ProverAgent and VerifierAgent
                verifier_agent = VerifierAgent()
                self.verifier_calls += 1
                
                verify_result = await verifier_agent.execute({
                    "requirements": extracted_reqs,
                    "logic_model": logic_model,
                    "state_machine": current_state_machine,
                })
                
                # Count prover calls (verifier uses prover internally)
                self.prover_calls += 1
                
                # Track contradictions and rejections
                if verify_result.get("result"):
                    report = verify_result["result"].get("verification_report", {})
                    issues = report.get("issues", [])
                    
                    for issue in issues:
                        if "contradiction" in str(issue.get("type", "")).lower():
                            self.contradictions_count += 1
                    
                    if not verify_result.get("is_consistent", True):
                        self.models_rejected += 1
                
                if verify_result.get("is_consistent", True):
                    break
                    
            except Exception as e:
                current_state_machine["error"] = str(e)
                break
        
        return current_state_machine, iterations


class NoProverVariant(AblationVariant):
    """
    V2: Without Z3 prover verification.
    
    Uses pipeline but skips ProverAgent Z3 checks.
    Verifier still runs but without formal proofs.
    """
    
    async def generate(self, requirements: str) -> Tuple[Dict[str, Any], int]:
        iterations = 0
        previous_states = None
        current_state_machine = {"states": [], "transitions": []}
        
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # 1. LLM Agent
                llm_agent = LLMAgent()
                llm_result = await llm_agent.execute({
                    "task_type": "extract_requirements",
                    "user_input": requirements
                })
                
                if not llm_result.get("success"):
                    break
                
                extracted_reqs = llm_result["result"]["requirements"]
                
                # 2. Logic Agent
                logic_agent = LogicAgent()
                logic_result = await logic_agent.execute({
                    "requirements": extracted_reqs
                })
                
                if not logic_result.get("success"):
                    break
                
                logic_model = logic_result["result"].get("logic_model", {})
                
                # 3. State Agent
                state_agent = StateAgent()
                state_agent.set_llm_agent(llm_agent)
                
                state_result = await state_agent.execute({
                    "logic_model": logic_model,
                    "requirements": extracted_reqs
                })
                
                if not state_result.get("success"):
                    break
                
                current_state_machine = state_result["result"].get("state_machine", {})
                
                # 4. Stability check
                current_states = set(
                    s.get("name", "") for s in current_state_machine.get("states", [])
                )
                
                if previous_states == current_states:
                    break
                
                previous_states = current_states
                
                # 5. Simplified verification WITHOUT Z3 prover
                # Only do basic structural checks
                self.verifier_calls += 1
                
                # Basic validation: check for required fields
                states = current_state_machine.get("states", [])
                has_initial = any(s.get("is_initial") for s in states)
                has_final = any(s.get("is_final") for s in states)
                
                # Track simple contradictions (same state initial and final)
                for state in states:
                    if state.get("is_initial") and state.get("is_final"):
                        self.contradictions_count += 1
                
                if has_initial and has_final:
                    break  # Basic structure OK
                    
            except Exception as e:
                current_state_machine["error"] = str(e)
                break
        
        return current_state_machine, iterations


class NoVerifierVariant(AblationVariant):
    """
    V3: Without consistency verifier.
    
    Uses pipeline but skips VerifierAgent entirely.
    No consistency checks or contradiction detection.
    """
    
    async def generate(self, requirements: str) -> Tuple[Dict[str, Any], int]:
        iterations = 0
        previous_states = None
        current_state_machine = {"states": [], "transitions": []}
        
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # 1. LLM Agent
                llm_agent = LLMAgent()
                llm_result = await llm_agent.execute({
                    "task_type": "extract_requirements",
                    "user_input": requirements
                })
                
                if not llm_result.get("success"):
                    break
                
                extracted_reqs = llm_result["result"]["requirements"]
                
                # 2. Logic Agent
                logic_agent = LogicAgent()
                logic_result = await logic_agent.execute({
                    "requirements": extracted_reqs
                })
                
                if not logic_result.get("success"):
                    break
                
                logic_model = logic_result["result"].get("logic_model", {})
                
                # 3. State Agent
                state_agent = StateAgent()
                state_agent.set_llm_agent(llm_agent)
                
                state_result = await state_agent.execute({
                    "logic_model": logic_model,
                    "requirements": extracted_reqs
                })
                
                if not state_result.get("success"):
                    break
                
                current_state_machine = state_result["result"].get("state_machine", {})
                
                # 4. Stability check only (NO VERIFIER)
                current_states = set(
                    s.get("name", "") for s in current_state_machine.get("states", [])
                )
                
                if previous_states == current_states:
                    break
                
                previous_states = current_states
                
                # Single iteration without verification loop
                break
                    
            except Exception as e:
                current_state_machine["error"] = str(e)
                break
        
        return current_state_machine, iterations


class NoSquareCompletionVariant(AblationVariant):
    """
    V4: Without square completion inference.
    
    LLM only extracts explicit relations from requirements.
    Does not infer missing A/E/I/O relations.
    """
    
    async def generate(self, requirements: str) -> Tuple[Dict[str, Any], int]:
        iterations = 0
        previous_states = None
        current_state_machine = {"states": [], "transitions": []}
        
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # 1. LLM Agent - Extract ONLY explicit requirements (no inference)
                llm_agent = LLMAgent()
                llm_result = await llm_agent.execute({
                    "task_type": "extract_requirements",
                    "user_input": requirements
                })
                
                if not llm_result.get("success"):
                    break
                
                extracted_reqs = llm_result["result"]["requirements"]
                
                # Remove any inferred relations - keep only explicit formulas
                if "formulas" in extracted_reqs:
                    # Keep only high-confidence (explicitly stated) formulas
                    extracted_reqs["formulas"] = [
                        f for f in extracted_reqs.get("formulas", [])
                        if f.get("confidence", 0) >= 0.9
                    ]
                
                # Skip square completion - do NOT call infer_logic_square
                
                # 2. Logic Agent with reduced formulas
                logic_agent = LogicAgent()
                logic_result = await logic_agent.execute({
                    "requirements": extracted_reqs
                })
                
                if not logic_result.get("success"):
                    break
                
                logic_model = logic_result["result"].get("logic_model", {})
                
                # 3. State Agent
                state_agent = StateAgent()
                state_agent.set_llm_agent(llm_agent)
                
                state_result = await state_agent.execute({
                    "logic_model": logic_model,
                    "requirements": extracted_reqs
                })
                
                if not state_result.get("success"):
                    break
                
                current_state_machine = state_result["result"].get("state_machine", {})
                
                # 4. Stability check
                current_states = set(
                    s.get("name", "") for s in current_state_machine.get("states", [])
                )
                
                if previous_states == current_states:
                    break
                
                previous_states = current_states
                
                # 5. Verify (full verifier, but with incomplete logic)
                verifier_agent = VerifierAgent()
                self.verifier_calls += 1
                
                verify_result = await verifier_agent.execute({
                    "requirements": extracted_reqs,
                    "logic_model": logic_model,
                    "state_machine": current_state_machine,
                })
                
                self.prover_calls += 1
                
                if verify_result.get("result"):
                    report = verify_result["result"].get("verification_report", {})
                    issues = report.get("issues", [])
                    
                    for issue in issues:
                        if "contradiction" in str(issue.get("type", "")).lower():
                            self.contradictions_count += 1
                    
                    if not verify_result.get("is_consistent", True):
                        self.models_rejected += 1
                
                if verify_result.get("is_consistent", True):
                    break
                    
            except Exception as e:
                current_state_machine["error"] = str(e)
                break
        
        return current_state_machine, iterations
