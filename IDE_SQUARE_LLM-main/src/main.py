import os

# Disable LangSmith tracing BEFORE any LangChain/LangGraph imports
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""
os.environ["LANGCHAIN_ENDPOINT"] = ""
os.environ["LANGCHAIN_PROJECT"] = ""

import typer
import asyncio
from rich.console import Console
from rich.table import Table
from typing import Optional

from src.config import config
from src.orchestration.langgraph_workflow import SquareIDEWorkflow

app = typer.Typer(name="square-ide", help="SQUARE IDE - LLM-driven Logic Modeling")
console = Console()


@app.command()
def process(
    requirements: str = typer.Argument(..., help="Requirements text to process"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
) -> None:
    """Process requirements and generate formal logic model."""
    
    if verbose:
        console.print(f"[green]Processing requirements:[/green] {requirements}")
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    
    # Run the workflow
    try:
        workflow = SquareIDEWorkflow()
        result = asyncio.run(workflow.run(requirements))
        
        # Display results
        _display_results(result, verbose)
        
        # Save to file if requested
        if output:
            _save_results(result, output)
            console.print(f"[green]Results saved to:[/green] {output}")
            
    except Exception as e:
        console.print(f"[red]Processing failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def validate(
    model_file: str = typer.Argument(..., help="Model file to validate")
) -> None:
    """Validate a generated model."""
    console.print(f"[yellow]Validating model:[/yellow] {model_file}")
    # TODO: Implement model validation


@app.command()
def experiment(
    experiment_type: str = typer.Argument(..., help="Experiment type: e1, e2, or e3"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Experiment config file")
) -> None:
    """Run experiments for evaluation."""
    console.print(f"[blue]Running experiment:[/blue] {experiment_type}")
    # TODO: Implement experiment runners


def _display_results(result: dict, verbose: bool) -> None:
    """Display processing results in a formatted table."""
    
    table = Table(title="SQUARE IDE Processing Results")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")
    
    # Logic Model
    logic_model = result.get("logic_model", {})
    if logic_model:
        relations_count = len(logic_model.get("relations", []))
        entities_count = len(logic_model.get("entities", []))
        table.add_row(
            "Logic Model", 
            "✓ Generated", 
            f"{relations_count} relations, {entities_count} entities"
        )
    
    # State Machine
    state_machine = result.get("state_machine", {})
    if state_machine:
        states_count = len(state_machine.get("states", []))
        transitions_count = len(state_machine.get("transitions", []))
        table.add_row(
            "State Machine", 
            "✓ Generated", 
            f"{states_count} states, {transitions_count} transitions"
        )
    
    # Verification
    verification_results = result.get("verification_results", [])
    if verification_results:
        verified = all(r.get("verified", False) for r in verification_results)
        status = "✓ Verified" if verified else "⚠ Issues Found"
        table.add_row("Verification", status, f"{len(verification_results)} checks")
    
    console.print(table)
    
    if verbose:
        console.print("\n[bold]Detailed Messages:[/bold]")
        for msg in result.get("messages", []):
            # Message content already includes agent name prefix
            console.print(f"[dim]{msg.get('role', 'system')}:[/dim] {msg['content']}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
) -> None:
    """Run the FastAPI agent service (HTTP + WebSocket)."""
    import uvicorn

    uvicorn.run("src.api.server:app", host=host, port=port, reload=False)


def _save_results(result: dict, output_path: str) -> None:
    """Save results to a file."""
    import json
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)


if __name__ == "__main__":
    app()