from langgraph.graph import StateGraph, END
from src.agents.llm_agent import LLMAgent
from src.agents.logic_agent import LogicAgent
from src.agents.state_agent import StateAgent
from pydantic import BaseModel
from typing import Any, Dict, Optional
import asyncio
import json
from rich.console import Console
from rich.table import Table
from rich.json import JSON

from dotenv import load_dotenv

load_dotenv()

console = Console()

llm_agent = LLMAgent()
logic_agent = LogicAgent()
state_agent = StateAgent()

# --- Schemat stanu workflow ---
class WorkflowState(BaseModel):
    user_input: Optional[str] = None
    requirements: Optional[Dict[str, Any]] = None
    logic_model: Optional[Dict[str, Any]] = None
    state_machine: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"

workflow = StateGraph(state_schema=WorkflowState)

def show_llm_result(requirements):
    table = Table(title="LLMAgent Result")
    table.add_column("Formulas", justify="center")
    table.add_column("Entities", justify="center")
    table.add_column("Ambiguities", justify="center")
    
    formulas = len(requirements.get("formulas", []))
    entities = ", ".join(requirements.get("entities", [])) or "-"
    ambiguities = ", ".join(requirements.get("ambiguities", [])) or "-"
    
    table.add_row(str(formulas), entities, ambiguities)
    console.print(table)

def show_logic_result(logic_result):
    table = Table(title="LogicAgent Result")
    table.add_column("Relations count", justify="center")
    table.add_column("Entities found", justify="center")
    table.add_column("Is consistent", justify="center")
    table.add_column("Contradictions", justify="center")

    relations = str(logic_result.get("relations_count", 0))
    entities = ", ".join(logic_result.get("entities_found", [])) or "-"
    consistent = "✅" if logic_result.get("is_consistent") else "❌"
    
    contradictions_list = logic_result.get("contradictions", [])
    if contradictions_list:
        contradictions = "\n".join([c["description"] for c in contradictions_list])
    else:
        contradictions = "-"

    table.add_row(relations, entities, consistent, contradictions)
    console.print(table)


def show_state_result(state_machine):
    table = Table(title="StateAgent Result")
    table.add_column("States", justify="left", style="cyan")
    table.add_column("Transitions", justify="left", style="green")
    
    states_detail = []
    for s in state_machine.get("states", []):
        state_str = s["name"]
        if s.get("properties"):
            props = ", ".join([f"{k}={v}" for k, v in s["properties"].items()])
            state_str += f" [{props}]"
        states_detail.append(state_str)
    
    states = "\n".join(states_detail) or "-"
    transitions = "\n".join([f'{t["from_state"]} → {t["to_state"]}: {t.get("condition", "N/A")}' 
                            for t in state_machine.get("transitions", [])]) or "-"
    
    table.add_row(states, transitions)
    console.print(table)
    
    if state_machine.get("metadata"):
        console.print("\n[yellow]Metadata:[/yellow]")
        console.print(state_machine["metadata"])

@workflow.add_node
async def llm_step(state: WorkflowState):
    result = await llm_agent.execute({
        "task_type": "extract_requirements",
        "user_input": state.user_input
    })
    if not result["success"]:
        raise RuntimeError(f"LLMAgent failed: {result['error_message']}")
    state.requirements = result["result"]["requirements"]
    show_llm_result(state.requirements)
    return state

@workflow.add_node
async def logic_step(state: WorkflowState):
    result = await logic_agent.execute({
        "requirements": state.requirements
    })
    if not result["success"]:
        raise RuntimeError(f"LogicAgent failed: {result['error_message']}")
    state.logic_model = result["result"]["logic_model"]
    show_logic_result(result["result"])
    return state

@workflow.add_node
async def state_step(state: WorkflowState):
    result = await state_agent.execute({
        "logic_model": state.logic_model,
        "requirements": state.requirements, 
        "llm_agent": llm_agent 
    })
    if not result["success"]:
        raise RuntimeError(f"StateAgent failed: {result['error_message']}")
    state.state_machine = result["result"]["state_machine"]
    show_state_result(state.state_machine)
    return state

workflow.add_edge("llm_step", "logic_step")
workflow.add_edge("logic_step", "state_step")
workflow.add_edge("state_step", END)
workflow.set_entry_point("llm_step")
workflow_app = workflow.compile()

async def main():
    user_input = """
    Hotel reservation system:
    - All premium rooms have a balcony
    - No occupied room is available for reservation
    - Some rooms have an ocean view
    - Not all rooms are air-conditioned
    
    A room can transition from available to reserved.
    A room can transition from reserved to occupied.
    """

    result = await workflow_app.ainvoke(
        {"user_input": user_input},
        configurable={"thread_id": "demo-run-1"} 
    )

    console.rule("[bold green]FINAL RESULT[/bold green]")
    console.print(f"Extracted requirements: {len(result['requirements'].get('formulas', []))}")
    console.print(f"Logic model entities: {result['logic_model'].get('entities', [])}")
    console.print(f"State machine states: {len(result['state_machine']['states'])}")
    console.print(f"State machine transitions: {len(result['state_machine']['transitions'])}")
    
    # Detailed output
    console.print("\n[bold cyan]Full State Machine:[/bold cyan]")
    console.print(JSON(json.dumps(result['state_machine'], indent=2)))

asyncio.run(main())
