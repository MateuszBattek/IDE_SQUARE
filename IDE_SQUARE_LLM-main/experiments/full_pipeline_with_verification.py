from langgraph.graph import StateGraph, END
from src.agents.llm_agent import LLMAgent
from src.agents.logic_agent import LogicAgent
from src.agents.class_agent import ClassAgent
from src.agents.prover_agent import ProverAgent
from src.agents.state_agent import StateAgent
from src.agents.verifier_agent import VerifierAgent
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
import json
from dotenv import load_dotenv

load_dotenv()

console = Console()

# Initialize agents
llm_agent = LLMAgent()
logic_agent = LogicAgent()
class_agent = ClassAgent()
prover_agent = ProverAgent()
state_agent = StateAgent()
verifier_agent = VerifierAgent()


# --- Workflow State Schema ---
class WorkflowState(BaseModel):
    user_input: Optional[str] = None
    requirements: Optional[Dict[str, Any]] = None
    logic_model: Optional[Dict[str, Any]] = None
    ontology: Optional[Dict[str, Any]] = None
    state_machine: Optional[Dict[str, Any]] = None
    verification_report: Optional[Dict[str, Any]] = None
    disjointness_checks: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = "allow"


workflow = StateGraph(state_schema=WorkflowState)

# --- Display Helper Functions ---


def show_llm_result(requirements):
    """Display LLM Agent extraction results."""
    console.rule("[bold blue]🤖 LLM Agent - Requirements Extraction[/bold blue]")

    table = Table(
        title="Extracted Requirements", show_header=True, header_style="bold magenta"
    )
    table.add_column("Type", justify="left", style="cyan")
    table.add_column("Subject", justify="left", style="green")
    table.add_column("Predicate", justify="left", style="yellow")
    table.add_column("Confidence", justify="center", style="blue")

    formulas = requirements.get("formulas", [])
    for formula in formulas:
        table.add_row(
            formula.get("type", "unknown"),
            formula.get("subject", "-"),
            formula.get("predicate", "-"),
            f"{formula.get('confidence', 0):.2f}",
        )

    console.print(table)
    console.print(
        f"[bold]Entities:[/bold] {', '.join(requirements.get('entities', []))}"
    )

    ambiguities = requirements.get("ambiguities", [])
    if ambiguities:
        console.print(
            f"[bold yellow]⚠️  Ambiguities:[/bold yellow] {', '.join(ambiguities)}"
        )
    else:
        console.print("[bold green]✅ No ambiguities detected[/bold green]")
    console.print()


def show_logic_result(logic_result):
    """Display Logic Agent results."""
    console.rule("[bold blue]🧠 Logic Agent - Square of Opposition[/bold blue]")

    table = Table(title="Logic Model", show_header=True, header_style="bold magenta")
    table.add_column("Metric", justify="left", style="cyan")
    table.add_column("Value", justify="left", style="green")

    table.add_row("Relations Count", str(logic_result.get("relations_count", 0)))
    table.add_row("Entities Found", ", ".join(logic_result.get("entities_found", [])))
    table.add_row("Is Consistent", "✅" if logic_result.get("is_consistent") else "❌")

    contradictions_list = logic_result.get("contradictions", [])
    if contradictions_list:
        contradictions = "\n".join([c["description"] for c in contradictions_list])
        table.add_row("Contradictions", f"[bold red]{contradictions}[/bold red]")
    else:
        table.add_row("Contradictions", "[green]None[/green]")

    console.print(table)
    console.print()


def show_ontology_result(ontology_result):
    """Display Class Agent ontology generation results."""
    console.rule("[bold blue]🏛️  Class Agent - Ontology Generation[/bold blue]")

    ontology = ontology_result.get("ontology", {})

    # Classes table
    classes_table = Table(
        title="Ontology Classes", show_header=True, header_style="bold magenta"
    )
    classes_table.add_column("Class Name", justify="left", style="cyan")
    classes_table.add_column("SubClass Of", justify="left", style="green")
    classes_table.add_column("Disjoint With", justify="left", style="red")

    for cls in ontology.get("classes", []):
        classes_table.add_row(
            cls.get("name", "-"),
            ", ".join(cls.get("subclass_of", [])) or "-",
            ", ".join(cls.get("disjoint_with", [])) or "-",
        )

    console.print(classes_table)

    # Properties table
    properties = ontology.get("properties", [])
    if properties:
        props_table = Table(
            title="Ontology Properties", show_header=True, header_style="bold magenta"
        )
        props_table.add_column("Property Name", justify="left", style="cyan")
        props_table.add_column("Domain", justify="left", style="green")
        props_table.add_column("Range", justify="left", style="yellow")
        props_table.add_column("Type", justify="left", style="blue")

        for prop in properties:
            props_table.add_row(
                prop.get("name", "-"),
                prop.get("domain", "-"),
                prop.get("range", "-"),
                prop.get("property_type", "-"),
            )

        console.print(props_table)

    console.print(
        f"\n[bold]Total Classes:[/bold] {ontology_result.get('classes_count', 0)}"
    )
    console.print(
        f"[bold]Total Properties:[/bold] {ontology_result.get('properties_count', 0)}"
    )
    console.print()


def show_disjointness_checks(disjointness_checks):
    """Display ProverAgent disjointness verification results."""
    console.rule("[bold blue]🔬 Prover Agent - Disjointness Verification[/bold blue]")

    table = Table(
        title="Disjointness Checks (Z3 SMT Solver)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Class A", justify="left", style="cyan")
    table.add_column("Class B", justify="left", style="yellow")
    table.add_column("Verified", justify="center", style="green")
    table.add_column("Proof Time", justify="center", style="blue")

    for check in disjointness_checks:
        relation = check.get("relation", {})
        result = check.get("result", {})
        verified = "✅" if check.get("verified", False) else "❌"
        proof_time = f"{result.get('proof_time_ms', 0)}ms"

        table.add_row(
            relation.get("subject", "-"),
            relation.get("predicate", "-"),
            verified,
            proof_time,
        )

    console.print(table)

    all_valid = all(check.get("verified", False) for check in disjointness_checks)
    if all_valid:
        console.print(
            "[bold green]✅ All disjointness assertions verified![/bold green]"
        )
    else:
        console.print(
            "[bold red]❌ Some disjointness assertions failed verification[/bold red]"
        )
    console.print()


def show_state_result(state_machine):
    """Display State Agent results."""
    console.rule("[bold blue]🔄 State Agent - State Machine Generation[/bold blue]")

    # States table
    states_table = Table(title="States", show_header=True, header_style="bold magenta")
    states_table.add_column("State Name", justify="left", style="cyan")
    states_table.add_column("Initial", justify="center", style="green")
    states_table.add_column("Final", justify="center", style="red")
    states_table.add_column("Description", justify="left", style="yellow")

    for state in state_machine.get("states", []):
        states_table.add_row(
            state.get("name", "-"),
            "✅" if state.get("is_initial", False) else "-",
            "✅" if state.get("is_final", False) else "-",
            state.get("description", "-"),
        )

    console.print(states_table)

    # Transitions table
    transitions_table = Table(
        title="Transitions", show_header=True, header_style="bold magenta"
    )
    transitions_table.add_column("From State", justify="left", style="cyan")
    transitions_table.add_column("→", justify="center", style="white")
    transitions_table.add_column("To State", justify="left", style="green")
    transitions_table.add_column("Condition", justify="left", style="yellow")

    for trans in state_machine.get("transitions", []):
        transitions_table.add_row(
            trans.get("from_state", "-"),
            "→",
            trans.get("to_state", "-"),
            trans.get("condition", "-"),
        )

    console.print(transitions_table)
    console.print()


def show_verification_result(verification_report):
    """Display Verifier Agent results."""
    console.rule(
        "[bold blue]✅ Verifier Agent - Comprehensive Verification[/bold blue]"
    )

    # Overall status
    is_consistent = verification_report.get("is_consistent", False)
    if is_consistent:
        console.print(
            Panel(
                "[bold green]✅ ALL MODELS ARE CONSISTENT[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[bold red]❌ INCONSISTENCIES DETECTED[/bold red]", border_style="red"
            )
        )

    # Statistics
    stats = verification_report.get("statistics", {})
    stats_table = Table(
        title="Verification Statistics", show_header=True, header_style="bold magenta"
    )
    stats_table.add_column("Metric", justify="left", style="cyan")
    stats_table.add_column("Value", justify="right", style="green")

    stats_table.add_row("Total Issues", str(stats.get("total_issues", 0)))
    stats_table.add_row("Errors", f"[bold red]{stats.get('errors', 0)}[/bold red]")
    stats_table.add_row(
        "Warnings", f"[bold yellow]{stats.get('warnings', 0)}[/bold yellow]"
    )
    stats_table.add_row("Total Fixes Proposed", str(stats.get("total_fixes", 0)))

    console.print(stats_table)

    # Issues
    issues = verification_report.get("issues", [])
    if issues:
        console.print("\n[bold yellow]📋 Issues Found:[/bold yellow]")
        issues_table = Table(show_header=True, header_style="bold magenta")
        issues_table.add_column("#", justify="center", style="cyan", width=4)
        issues_table.add_column("Type", justify="left", style="yellow")
        issues_table.add_column("Severity", justify="center", style="red")
        issues_table.add_column("Description", justify="left", style="white")
        issues_table.add_column("Location", justify="left", style="blue")

        for i, issue in enumerate(issues, 1):
            severity_color = {
                "error": "[bold red]ERROR[/bold red]",
                "warning": "[bold yellow]WARN[/bold yellow]",
                "info": "[bold blue]INFO[/bold blue]",
            }.get(issue.get("severity", "info"), issue.get("severity", ""))

            issues_table.add_row(
                str(i),
                issue.get("issue_type", "-"),
                severity_color,
                issue.get("description", "-"),
                issue.get("location", "-"),
            )

        console.print(issues_table)
    else:
        console.print("\n[bold green]✅ No issues detected![/bold green]")

    # Fixes
    fixes = verification_report.get("fixes", [])
    if fixes:
        console.print("\n[bold cyan]🔧 Proposed Fixes:[/bold cyan]")
        fixes_table = Table(show_header=True, header_style="bold magenta")
        fixes_table.add_column("#", justify="center", style="cyan", width=4)
        fixes_table.add_column("Fix Type", justify="left", style="green")
        fixes_table.add_column("Description", justify="left", style="white")
        fixes_table.add_column("Confidence", justify="center", style="yellow")
        fixes_table.add_column("User Input?", justify="center", style="red")

        for i, fix in enumerate(fixes, 1):
            fixes_table.add_row(
                str(i),
                fix.get("fix_type", "-"),
                fix.get("description", "-"),
                f"{fix.get('confidence', 0):.2f}",
                "✅" if fix.get("requires_user_input", True) else "❌",
            )

        console.print(fixes_table)

    console.print()


# --- Workflow Nodes ---


@workflow.add_node
async def llm_step(state: WorkflowState):
    """Step 1: Extract requirements using LLM Agent."""
    result = await llm_agent.execute(
        {"task_type": "extract_requirements", "user_input": state.user_input}
    )
    if not result["success"]:
        raise RuntimeError(f"LLMAgent failed: {result['error_message']}")
    state.requirements = result["result"]["requirements"]
    show_llm_result(state.requirements)
    return state


@workflow.add_node
async def logic_step(state: WorkflowState):
    """Step 2: Generate logic model using Logic Agent."""
    result = await logic_agent.execute({"requirements": state.requirements})
    if not result["success"]:
        raise RuntimeError(f"LogicAgent failed: {result['error_message']}")
    state.logic_model = result["result"]["logic_model"]
    show_logic_result(result["result"])
    return state


@workflow.add_node
async def ontology_step(state: WorkflowState):
    """Step 3: Generate ontology using Class Agent (with ProverAgent verification)."""
    result = await class_agent.execute({"logic_model": state.logic_model})
    if not result["success"]:
        raise RuntimeError(f"ClassAgent failed: {result['error_message']}")
    state.ontology = result["result"]["ontology"]
    state.disjointness_checks = result["result"]["disjointness_checks"]
    show_ontology_result(result["result"])
    show_disjointness_checks(state.disjointness_checks)
    return state


@workflow.add_node
async def state_step(state: WorkflowState):
    """Step 4: Generate state machine using State Agent."""
    result = await state_agent.execute({
        "logic_model": state.logic_model,
        "requirements": state.requirements
    })
    if not result["success"]:
        raise RuntimeError(f"StateAgent failed: {result['error_message']}")
    state.state_machine = result["result"]["state_machine"]
    show_state_result(state.state_machine)
    return state


@workflow.add_node
async def verification_step(state: WorkflowState):
    """Step 5: Verify all models using Verifier Agent."""
    result = await verifier_agent.execute(
        {
            "logic_model": state.logic_model,
            "ontology": state.ontology,
            "state_machine": state.state_machine,
            "requirements": state.requirements,
        }
    )
    if not result["success"]:
        raise RuntimeError(f"VerifierAgent failed: {result['error_message']}")
    state.verification_report = result["result"]["verification_report"]
    show_verification_result(state.verification_report)
    return state


# --- Workflow Edges ---
workflow.add_edge("llm_step", "logic_step")
workflow.add_edge("logic_step", "ontology_step")
workflow.add_edge("ontology_step", "state_step")
workflow.add_edge("state_step", "verification_step")
workflow.add_edge("verification_step", END)
workflow.set_entry_point("llm_step")
workflow_app = workflow.compile()

# --- Main Execution ---


async def main():
    console.clear()
    console.print(
        Panel.fit(
            "[bold cyan]🚀 SQUARE IDE - Full Pipeline Experiment[/bold cyan]\n"
            "[white]Logic → Ontology → State Machine → Verification[/white]\n"
            "[dim]With ProverAgent (Z3 SMT Solver) + ClassAgent + VerifierAgent[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # Test input: Hotel reservation system
    user_input = """
    Hotel reservation system requirements:
    
    Logical Relations:
    - All premium rooms have a balcony
    - No occupied room is available for reservation
    - Some rooms have an ocean view
    - Some rooms are not air-conditioned
    - All deluxe rooms are premium rooms
    - No budget rooms are premium rooms
    
    State Transitions:
    - A room can transition from available to reserved
    - A room can transition from reserved to occupied
    - A room can transition from occupied to cleaning
    - A room can transition from cleaning to available
    
    Entities: room, premium_room, deluxe_room, budget_room, occupied_room, available_room
    """

    console.print(
        Panel(user_input, title="[bold]User Input[/bold]", border_style="blue")
    )
    console.print()

    # Run workflow
    result = await workflow_app.ainvoke(
        {"user_input": user_input},
        {"configurable": {"thread_id": "full-pipeline-demo"}},
    )

    # Final summary
    console.rule("[bold green]📊 FINAL PIPELINE SUMMARY[/bold green]")

    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Stage", justify="left", style="cyan", width=20)
    summary_table.add_column("Output", justify="left", style="white")

    summary_table.add_row(
        "1. Requirements",
        f"{len(result['requirements'].get('formulas', []))} logical formulas extracted",
    )
    summary_table.add_row(
        "2. Logic Model",
        f"{len(result['logic_model'].get('relations', []))} relations, {len(result['logic_model'].get('entities', []))} entities",
    )
    summary_table.add_row(
        "3. Ontology",
        f"{len(result['ontology'].get('classes', []))} classes, {len(result['ontology'].get('properties', []))} properties",
    )
    summary_table.add_row(
        "4. State Machine",
        f"{len(result['state_machine']['states'])} states, {len(result['state_machine']['transitions'])} transitions",
    )
    summary_table.add_row(
        "5. Verification",
        f"{'✅ CONSISTENT' if result['verification_report']['is_consistent'] else '❌ INCONSISTENT'} - "
        f"{result['verification_report']['statistics']['total_issues']} issues found",
    )

    console.print(summary_table)

    # Export final result
    console.print("\n[bold]Exporting results to JSON...[/bold]")
    output_file = "experiments/output/full_pipeline_result.json"
    import os

    os.makedirs("experiments/output", exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, default=str)

    console.print(f"[green]✅ Results saved to: {output_file}[/green]")
    console.print()

    console.print(
        Panel.fit(
            "[bold green]✨ Pipeline execution completed successfully![/bold green]\n"
            "[white]All agents executed: LLM → Logic → Class+Prover → State → Verifier[/white]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
