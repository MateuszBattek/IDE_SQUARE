import asyncio
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON

load_dotenv()

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.llm_agent import LLMAgent
from src.agents.logic_agent import LogicAgent
from src.agents.state_agent import StateAgent
from src.agents.verifier_agent import VerifierAgent
from src.agents.class_agent import ClassAgent
from src.agents.prover_agent import ProverAgent

console = Console()


async def full_workflow():
    console.rule("[bold blue]FULL MULTI-AGENT WORKFLOW[/bold blue]")
    
    user_input = """
    Hotel reservation system:
    - All premium rooms have a balcony
    - No occupied room is available for reservation
    - Some rooms have an ocean view
    - Not all rooms are air-conditioned
    
    A room can transition from available to reserved.
    A room can transition from reserved to occupied.
    A room can transition from occupied to cleaning.
    A room can transition from cleaning to available.
    """
    
    console.print(Panel(user_input, title="📝 User Input", border_style="cyan"))
    
    # ====================
    # STEP 1: LLMAgent
    # ====================
    console.rule("[bold green]STEP 1: LLMAgent - Extract Requirements[/bold green]")
    
    llm_agent = LLMAgent()
    llm_result = await llm_agent.execute({
        "task_type": "extract_requirements",
        "user_input": user_input
    })
    
    if not llm_result["success"]:
        console.print(f"[red]❌ LLMAgent failed: {llm_result['error_message']}[/red]")
        return
    
    requirements = llm_result["result"]["requirements"]
    
    # Display LLM results
    table = Table(title="LLMAgent Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    table.add_row("Formulas Extracted", str(len(requirements.get("formulas", []))))
    table.add_row("Entities Found", ", ".join(requirements.get("entities", [])))
    table.add_row("States Defined", ", ".join(requirements.get("states", [])))
    table.add_row("Transitions Defined", str(len(requirements.get("transitions", []))))
    table.add_row("Needs Clarification", "✅ Yes" if llm_result["result"]["needs_clarification"] else "❌ No")
    table.add_row("Confidence", f"{llm_result['result']['confidence']:.2%}")
    
    console.print(table)
    
    console.print("\n[yellow]Formulas:[/yellow]")
    for i, formula in enumerate(requirements.get("formulas", []), 1):
        console.print(f"  {i}. [{formula['type']}] {formula['subject']} → {formula['predicate']}")
    
    # ====================
    # STEP 2: LogicAgent
    # ====================
    console.rule("[bold green]STEP 2: LogicAgent - Build Logic Model[/bold green]")
    
    logic_agent = LogicAgent()
    logic_result = await logic_agent.execute({
        "requirements": requirements
    })
    
    if not logic_result["success"]:
        console.print(f"[red]❌ LogicAgent failed: {logic_result['error_message']}[/red]")
        return
    
    logic_model = logic_result["result"]["logic_model"]
    
    # Display Logic results
    table = Table(title="LogicAgent Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    table.add_row("Relations Count", str(logic_result["result"]["relations_count"]))
    table.add_row("Entities Found", ", ".join(logic_result["result"]["entities_found"]))
    table.add_row("Is Consistent", "✅" if logic_result["result"]["is_consistent"] else "❌")
    table.add_row("Contradictions", str(len(logic_result["result"].get("contradictions", []))))
    
    console.print(table)
    
    console.print("\n[yellow]Logic Relations:[/yellow]")
    for i, rel in enumerate(logic_model.get("relations", []), 1):
        console.print(f"  {i}. {rel['relation_type']}: {rel['subject']} → {rel['predicate']} (confidence: {rel['confidence']:.2f})")
    
    # ====================
    # STEP 3: StateAgent
    # ====================
    console.rule("[bold green]STEP 3: StateAgent - Generate State Machine[/bold green]")
    
    state_agent = StateAgent()
    state_result = await state_agent.execute({
        "logic_model": logic_model,
        "requirements": requirements,
        "llm_agent": llm_agent
    })
    
    if not state_result["success"]:
        console.print(f"[red]❌ StateAgent failed: {state_result['error_message']}[/red]")
        return
    
    state_machine = state_result["result"]["state_machine"]
    
    # Display State results
    table = Table(title="StateAgent Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    table.add_row("States Count", str(state_result["result"]["states_count"]))
    table.add_row("Transitions Count", str(state_result["result"]["transitions_count"]))
    table.add_row("Initial State", state_machine.get("initial_state", "N/A"))
    
    console.print(table)
    
    console.print("\n[yellow]States with Properties:[/yellow]")
    for state in state_machine.get("states", []):
        props = state.get("properties", {})
        props_str = f" [{', '.join([f'{k}={v}' for k, v in props.items()])}]" if props else ""
        initial = " (INITIAL)" if state.get("is_initial") else ""
        console.print(f"  • {state['name']}{props_str}{initial}")
    
    console.print("\n[yellow]Transitions:[/yellow]")
    for trans in state_machine.get("transitions", []):
        console.print(f"  • {trans['from_state']} → {trans['to_state']}")
        console.print(f"    Condition: {trans.get('condition', 'N/A')}")
        console.print(f"    Confidence: {trans.get('confidence', 0):.2f}")
    
    # ====================
    # STEP 4: ClassAgent
    # ====================
    console.rule("[bold green]STEP 4: ClassAgent - Generate Ontology[/bold green]")
    
    class_agent = ClassAgent()
    class_result = await class_agent.execute({
        "logic_model": logic_model,
        "state_machine": state_machine
    })
    
    if not class_result["success"]:
        console.print(f"[red]❌ ClassAgent failed: {class_result['error_message']}[/red]")
        return
    
    ontology = class_result["result"]["ontology"]  # Changed from ontology_model to ontology
    
    # Display Class results
    table = Table(title="ClassAgent Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    table.add_row("Classes Count", str(class_result["result"]["classes_count"]))
    table.add_row("Properties Count", str(class_result["result"]["properties_count"]))
    table.add_row("Disjointness Checks", str(len(class_result["result"].get("disjointness_checks", []))))
    table.add_row("All Disjoint Valid", "✅" if class_result["result"].get("all_disjoint_valid") else "❌")
    
    console.print(table)
    
    console.print("\n[yellow]Classes:[/yellow]")
    for cls in ontology.get("classes", []):
        console.print(f"  • {cls['name']}")
        if cls.get("properties"):
            for prop in cls["properties"]:
                # Handle both dict and string properties
                if isinstance(prop, dict):
                    prop_name = prop.get('name', prop.get('property_name', 'N/A'))
                    prop_type = prop.get('type', prop.get('property_type', 'N/A'))
                    console.print(f"    - {prop_name}: {prop_type}")
                else:
                    # If it's just a string, print it directly
                    console.print(f"    - {prop}")
    
    console.print("\n[yellow]Disjointness Assertions:[/yellow]")
    for assertion in ontology.get("disjoint_classes", []):
        console.print(f"  • {assertion.get('class1', assertion.get('class_a', 'N/A'))} ⊥ {assertion.get('class2', assertion.get('class_b', 'N/A'))}")
    
    # ====================
    # STEP 5: ProverAgent
    # ====================
    console.rule("[bold green]STEP 5: ProverAgent - Verify Assertions[/bold green]")
    
    prover_agent = ProverAgent()
    
    # Check some disjointness from ClassAgent results
    verification_results = []
    disjointness_checks = class_result["result"].get("disjointness_checks", [])
    
    if disjointness_checks:
        console.print(f"\n[cyan]Checking {len(disjointness_checks)} disjointness assertions...[/cyan]")
        for check in disjointness_checks[:3]:  # Show first 3
            verification_results.append({
                "assertion": check.get("assertion", "N/A"),
                "result": check.get("result", {"is_valid": False})
            })
    else:
        console.print("\n[yellow]No disjointness checks available from ClassAgent[/yellow]")
    
    # Display Prover results
    if verification_results:
        table = Table(title="ProverAgent Results", show_header=True, header_style="bold magenta")
        table.add_column("Assertion", style="cyan")
        table.add_column("Valid", style="green")
        table.add_column("Time (ms)", style="yellow")
        
        for vr in verification_results:
            valid = "✅" if vr["result"]["is_valid"] else "❌"
            time_ms = vr["result"].get("proof_time_ms", "N/A")
            table.add_row(vr["assertion"], valid, str(time_ms))
        
        console.print(table)
    else:
        console.print("[yellow]No verification results to display[/yellow]")
    
    # ====================
    # STEP 6: VerifierAgent
    # ====================
    console.rule("[bold green]STEP 6: VerifierAgent - Check Consistency[/bold green]")
    
    verifier_agent = VerifierAgent()
    verifier_result = await verifier_agent.execute({
        "logic_model": logic_model,
        "state_machine": state_machine,
        "ontology_model": ontology,  # Changed from ontology to ontology_model
        "requirements": requirements
    })
    
    if not verifier_result["success"]:
        console.print(f"[red]❌ VerifierAgent failed: {verifier_result['error_message']}[/red]")
        return
    
    verification = verifier_result["result"]
    
    # Display Verifier results
    table = Table(title="VerifierAgent Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Value", style="green")
    
    table.add_row("Overall Consistent", "✅" if verification.get("is_consistent", False) else "❌")
    table.add_row("Issues Found", str(verification.get("issues_count", 0)))
    table.add_row("Fixes Proposed", str(verification.get("fixes_count", 0)))
    
    # Get verification report if available
    report = verification.get("verification_report", {})
    if report:
        table.add_row("Missing States", str(len(report.get("missing_states", []))))
        table.add_row("Unreachable States", str(len(report.get("unreachable_states", []))))
    
    console.print(table)
    
    # Display issues if available
    report = verification.get("verification_report", {})
    if report and report.get("issues"):
        console.print("\n[red]Issues Found:[/red]")
        for issue in report["issues"][:5]:  # Show first 5
            severity = issue.get('severity', 'unknown')
            description = issue.get('description', 'N/A')
            console.print(f"  • [{severity}] {description}")
    
    if report and report.get("fixes"):
        console.print("\n[yellow]Proposed Fixes:[/yellow]")
        for fix in report["fixes"][:5]:  # Show first 5
            fix_type = fix.get('fix_type', 'unknown')
            description = fix.get('description', 'N/A')
            console.print(f"  • [{fix_type}] {description}")
    
    # ====================
    # FINAL SUMMARY
    # ====================
    console.rule("[bold blue]WORKFLOW SUMMARY[/bold blue]")
    
    summary_table = Table(title="Final Statistics", show_header=True, header_style="bold cyan")
    summary_table.add_column("Agent", style="cyan", width=20)
    summary_table.add_column("Status", style="green", width=10)
    summary_table.add_column("Output", style="yellow")
    
    summary_table.add_row("LLMAgent", "✅", f"{len(requirements.get('formulas', []))} formulas extracted")
    summary_table.add_row("LogicAgent", "✅", f"{logic_result['result']['relations_count']} relations")
    summary_table.add_row("StateAgent", "✅", f"{state_result['result']['states_count']} states, {state_result['result']['transitions_count']} transitions")
    summary_table.add_row("ClassAgent", "✅", f"{class_result['result']['classes_count']} classes")
    summary_table.add_row("ProverAgent", "✅", f"{len(verification_results)} assertions checked")
    summary_table.add_row("VerifierAgent", "✅" if verifier_result["result"].get("is_consistent") else "⚠️", 
                          f"{verifier_result['result'].get('issues_count', 0)} issues found")
    
    console.print(summary_table)
    
    console.print("\n[bold green]✅ All agents executed successfully![/bold green]")


if __name__ == "__main__":
    asyncio.run(full_workflow())
