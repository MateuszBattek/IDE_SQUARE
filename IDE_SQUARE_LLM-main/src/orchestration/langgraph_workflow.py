import os
import uuid

# Disable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class WorkflowState(BaseModel):
    requirements: str = ""  # Original user input (raw text)
    extracted_requirements: Dict[str, Any] = Field(default_factory=dict)  # Parsed by LLMAgent
    logic_model: Dict[str, Any] = Field(default_factory=dict)
    ontology_model: Dict[str, Any] = Field(default_factory=dict)
    state_machine: Dict[str, Any] = Field(default_factory=dict)
    verification_results: List[Dict[str, Any]] = Field(default_factory=list)
    clarifications_needed: List[str] = Field(default_factory=list)
    current_agent: str = ""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 5
    # E3 experiment tracking
    clarification_rounds: int = 0  # Number of times clarification was requested


class SquareIDEWorkflow:
    def __init__(self, checkpointer: Optional[object] = None):
        self.graph = None
        # Allow external checkpointers (e.g., SQLite) for session persistence
        self.memory = checkpointer or MemorySaver()
        self._setup_workflow()

    def _setup_workflow(self) -> None:
        workflow = StateGraph(WorkflowState)

        # Add nodes for each agent
        workflow.add_node("llm_coordinator", self._llm_coordinator_node)
        workflow.add_node("logic_processor", self._logic_processor_node)
        workflow.add_node("class_generator", self._class_generator_node)
        workflow.add_node("state_generator", self._state_generator_node)
        workflow.add_node("verifier", self._verifier_node)
        workflow.add_node("clarification", self._clarification_node)

        # Define the workflow edges
        workflow.add_edge(START, "llm_coordinator")

        # Conditional routing from coordinator
        workflow.add_conditional_edges(
            "llm_coordinator",
            self._route_from_coordinator,
            {"logic": "logic_processor", "clarify": "clarification", "complete": END},
        )

        # Logic processor routes to class generator
        workflow.add_edge("logic_processor", "class_generator")

        # Class generator routes to state generator
        workflow.add_edge("class_generator", "state_generator")

        # State generator routes to verifier
        workflow.add_edge("state_generator", "verifier")

        # Verifier routes back to coordinator for next iteration
        workflow.add_edge("verifier", "llm_coordinator")

        # Clarification routes back to coordinator
        workflow.add_edge("clarification", "llm_coordinator")

        self.graph = workflow.compile(checkpointer=self.memory)

    async def _llm_coordinator_node(self, state: WorkflowState) -> Dict[str, Any]:
        from ..agents.llm_agent import LLMAgent

        state.current_agent = "LLMAgent"
        state.iteration_count += 1

        if state.iteration_count > state.max_iterations:
            logger.warning("Maximum iterations reached, ending workflow")
            return {"current_agent": "END"}

        agent = LLMAgent()

        # Determine what the coordinator should do based on current state
        if not state.logic_model:
            # First iteration - extract requirements from user input
            input_data = {
                "task_type": "extract_requirements",
                "user_input": state.requirements,
            }
        else:
            # Subsequent iterations - coordinate next steps
            input_data = {
                "task_type": "coordinate_agents",
                "agent_results": {
                    "logic_model": state.logic_model,
                    "ontology_model": state.ontology_model,
                    "state_machine": state.state_machine,
                    "verification_results": state.verification_results,
                },
                "goal": "Generate complete formal model from requirements",
            }

        result = await agent.execute(input_data)

        if result["success"]:
            # Store extracted requirements for LogicAgent
            if "requirements" in result["result"]:
                state.extracted_requirements = result["result"]["requirements"]
            state.messages.append(
                {"role": "assistant", "content": f"LLMAgent: Extracted requirements"}
            )

        return state.model_dump()

    async def _logic_processor_node(self, state: WorkflowState) -> Dict[str, Any]:
        from ..agents.logic_agent import LogicAgent

        state.current_agent = "LogicAgent"
        agent = LogicAgent()

        # Use extracted requirements dict from LLMAgent
        input_data = {"requirements": state.extracted_requirements}
        result = await agent.execute(input_data)

        if result["success"]:
            state.logic_model = result["result"]["logic_model"]
            state.messages.append(
                {
                    "role": "assistant",
                    "content": f"LogicAgent: Extracted {result['result']['relations_count']} relations",
                }
            )

        return state.model_dump()

    async def _class_generator_node(self, state: WorkflowState) -> Dict[str, Any]:
        from ..agents.class_agent import ClassAgent

        state.current_agent = "ClassAgent"
        agent = ClassAgent()

        input_data = {"logic_model": state.logic_model}
        result = await agent.execute(input_data)

        if result["success"]:
            state.ontology_model = result["result"]["ontology"]

            # Include prover results in messages if available
            prover_summary = result["result"].get("prover_summary", {})
            total_checks = prover_summary.get("total_checks", 0)
            passed_checks = prover_summary.get("passed_checks", 0)

            state.messages.append(
                {
                    "role": "assistant",
                    "content": f"ClassAgent: Generated {result['result']['classes_count']} classes, {result['result']['properties_count']} properties. Formal verification: {passed_checks}/{total_checks} checks passed",
                }
            )

        return state.model_dump()

    async def _state_generator_node(self, state: WorkflowState) -> Dict[str, Any]:
        from ..agents.state_agent import StateAgent

        state.current_agent = "StateAgent"
        agent = StateAgent()

        # Pass both logic_model AND extracted_requirements so StateAgent can use explicit states/transitions
        input_data = {
            "logic_model": state.logic_model,
            "requirements": state.extracted_requirements
        }
        result = await agent.execute(input_data)

        if result["success"]:
            state.state_machine = result["result"]["state_machine"]
            state.messages.append(
                {
                    "role": "assistant",
                    "content": f"StateAgent: Generated {result['result']['states_count']} states, {result['result']['transitions_count']} transitions",
                }
            )

        return state.model_dump()

    async def _verifier_node(self, state: WorkflowState) -> Dict[str, Any]:
        from ..agents.verifier_agent import VerifierAgent

        state.current_agent = "VerifierAgent"
        agent = VerifierAgent()

        # Prepare comprehensive input for verification
        # Use extracted_requirements (dict) instead of requirements (string)
        input_data = {
            "requirements": state.extracted_requirements,
            "logic_model": state.logic_model,
            "ontology": state.ontology_model,
            "state_machine": state.state_machine,
        }

        result = await agent.execute(input_data)

        if result["success"]:
            verification_report = result["result"]["verification_report"]

            # Store verification results
            state.verification_results.append(
                {
                    "timestamp": "current",  # Could add actual timestamp
                    "is_consistent": verification_report.get("is_consistent", False),
                    "issues": verification_report.get("issues", []),
                    "fixes": verification_report.get("fixes", []),
                    "statistics": verification_report.get("statistics", {}),
                }
            )

            # Create summary message
            issues = verification_report.get("issues", [])
            issues_count = len(issues)
            errors = sum(1 for i in issues if i.get("severity") == "error")
            warnings = sum(1 for i in issues if i.get("severity") == "warning")

            state.messages.append(
                {
                    "role": "assistant",
                    "content": f"VerifierAgent: Consistent={verification_report.get('is_consistent')}, Issues={issues_count} ({errors} errors, {warnings} warnings)",
                }
            )

        return state.model_dump()

    async def _clarification_node(self, state: WorkflowState) -> Dict[str, Any]:
        from ..agents.llm_agent import LLMAgent

        state.current_agent = "ClarificationAgent"
        state.clarification_rounds += 1  # Track clarification rounds for E3 experiment
        agent = LLMAgent()

        input_data = {
            "task_type": "clarify_ambiguity",
            "text": state.requirements,
            "context": "SQUARE logic modeling",
        }

        result = await agent.execute(input_data)

        if result["success"]:
            state.clarifications_needed.append(
                result["result"]["clarification_questions"]
            )

        return state.model_dump()

    def _route_from_coordinator(self, state: WorkflowState) -> str:
        # Simple routing logic based on current state
        if not state.logic_model and state.iteration_count == 1:
            return "logic"
        elif state.clarifications_needed and not state.logic_model:
            return "clarify"
        elif state.iteration_count >= state.max_iterations:
            return "complete"
        elif (
            state.logic_model
            and state.ontology_model
            and state.state_machine
            and state.verification_results
        ):
            # All models generated and verified
            return "complete"
        else:
            return "logic"

    async def run(self, requirements: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the workflow for the provided requirements.

        session_id enables persistence/resume when using an external checkpointer.
        """
        initial_state = WorkflowState(requirements=requirements)

        session = session_id or f"square-ide-session-{uuid.uuid4()}"
        config = {"configurable": {"thread_id": session}}

        final_state = await self.graph.ainvoke(
            initial_state.model_dump(), config=config
        )

        # Attach session_id so callers can reference persisted state
        final_state["session_id"] = session
        return final_state
