"""
E2 Baseline Comparison Experiment - Main Runner

Compares three approaches for state machine generation:
- B1: Single-LLM (direct generation)
- B2: Manual Square Logic (rule-based)
- S:  Square-Bot (full MAS-LLM pipeline)

Usage:
    python -m experiments.e2_baseline_comparison
    python experiments/e2_baseline_comparison/main.py
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.evaluation.metrics import calculate_f1_states, calculate_f1_transitions, calculate_disjointness

from .models import ApproachType, E2ApproachResult, E2ModelComparison, E2ExperimentSummary
from .approaches import SingleLLMApproach, ManualSquareApproach, SquareBotApproach
from .disjointness import check_disjointness

console = Console()


# ============================================================================
# Reference Models Loader
# ============================================================================

def load_reference_models() -> Dict[str, Dict[str, Any]]:
    """Load reference models from test data."""
    ref_path = project_root / "experiments" / "test_data" / "e1_reference_models.json"
    
    if ref_path.exists():
        with open(ref_path) as f:
            data = json.load(f)
        
        # Convert array format to dict keyed by name
        if "reference_models" in data:
            models = {}
            for model in data["reference_models"]:
                name = model["name"]
                # Extract state names from expected_states objects
                expected_states = [
                    s["name"] if isinstance(s, dict) else s 
                    for s in model.get("expected_states", [])
                ]
                models[name] = {
                    "description": model.get("description", ""),
                    "requirements": model.get("requirements", ""),
                    "expected_states": expected_states,
                    "expected_transitions": len(model.get("expected_transitions", [])),
                }
            return models
        
        return data
    
    # Fallback minimal set
    console.print("[yellow]⚠ Reference models not found, using minimal set[/yellow]")
    return {
        "order_lifecycle": {
            "description": "Order processing with states: new, pending, confirmed, shipped, delivered, cancelled",
            "requirements": "An order starts as new, becomes pending after payment, confirmed when processed, shipped when dispatched, and delivered when received. Orders can be cancelled at any point before shipping.",
            "expected_states": ["new", "pending", "confirmed", "shipped", "delivered", "cancelled"],
            "expected_transitions": 8
        }
    }


# ============================================================================
# Approach Execution
# ============================================================================

async def run_approach(
    approach_type: ApproachType,
    requirements: str,
    model_name: str,
) -> E2ApproachResult:
    """
    Run a single approach and return results.
    """
    console.print(f"  [dim]Running {approach_type.value}...[/dim]")
    
    start_time = datetime.now()
    
    try:
        if approach_type == ApproachType.B1_SINGLE_LLM:
            approach = SingleLLMApproach()
        elif approach_type == ApproachType.B2_MANUAL_SQUARE:
            approach = ManualSquareApproach()
        else:
            approach = SquareBotApproach()
        
        state_machine, iterations = await approach.generate(requirements)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return E2ApproachResult(
            approach=approach_type,
            model_name=model_name,
            generated_machine=state_machine,
            iterations=iterations,
            execution_time=elapsed,
            error=state_machine.get("error"),
        )
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        return E2ApproachResult(
            approach=approach_type,
            model_name=model_name,
            generated_machine={"states": [], "transitions": []},
            iterations=0,
            execution_time=elapsed,
            error=str(e),
        )


async def compare_approaches(
    model_name: str,
    model_data: Dict[str, Any],
) -> E2ModelComparison:
    """
    Compare all three approaches on a single model.
    """
    requirements = model_data["requirements"]
    # Normalize expected states to lowercase
    expected_states = set(s.lower() for s in model_data["expected_states"])
    expected_transitions = model_data.get("expected_transitions", 0)
    
    # Run all approaches
    results: Dict[ApproachType, E2ApproachResult] = {}
    
    for approach_type in ApproachType:
        result = await run_approach(approach_type, requirements, model_name)
        results[approach_type] = result
    
    # Calculate metrics
    metrics: Dict[ApproachType, Dict[str, Any]] = {}
    
    for approach_type, result in results.items():
        # Normalize to lowercase for comparison
        generated_states = set(
            s.get("name", "").lower() for s in result.generated_machine.get("states", [])
        )
        generated_transitions = result.generated_machine.get("transitions", [])
        
        # F1 for states (case-insensitive comparison)
        if len(expected_states) > 0 or len(generated_states) > 0:
            precision = (
                len(expected_states & generated_states) / len(generated_states)
                if generated_states else 0
            )
            recall = (
                len(expected_states & generated_states) / len(expected_states)
                if expected_states else 0
            )
            f1_states = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0 else 0
            )
        else:
            f1_states = 0.0
        
        # Check disjointness
        disjoint_result = check_disjointness(result.generated_machine)
        disjoint_rate = (
            disjoint_result.passed_checks / disjoint_result.total_checks
            if disjoint_result.total_checks > 0 else 0.0
        )
        
        metrics[approach_type] = {
            "f1_states": f1_states,
            "f1_transitions": 0.5,  # Simplified for now
            "disjointness_pass": disjoint_result.passed,
            "disjointness_rate": disjoint_rate,
            "iterations": result.iterations,
        }
    
    return E2ModelComparison(
        model_name=model_name,
        description=model_data.get("description", ""),
        results=results,
        metrics=metrics,
    )


# ============================================================================
# Experiment Runner
# ============================================================================

async def run_e2_experiment(
    models: Dict[str, Dict[str, Any]] = None,
    output_file: Path = None,
) -> E2ExperimentSummary:
    """
    Run the full E2 experiment.
    
    Args:
        models: Optional custom models dict. If None, loads reference models.
        output_file: Optional path to save results JSON.
    
    Returns:
        E2ExperimentSummary with all results
    """
    console.print(Panel.fit(
        "[bold cyan]E2 Experiment: Baseline vs Square-Bot[/bold cyan]\n"
        "Comparing B1 (Single-LLM), B2 (Manual Square), S (Square-Bot)",
        border_style="cyan"
    ))
    
    if models is None:
        models = load_reference_models()
    
    console.print(f"\n[bold]Testing {len(models)} models...[/bold]\n")
    
    comparisons: List[E2ModelComparison] = []
    
    for model_name, model_data in models.items():
        console.print(f"[bold blue]📋 {model_name}[/bold blue]")
        comparison = await compare_approaches(model_name, model_data)
        comparisons.append(comparison)
        console.print()
    
    # Aggregate results
    summary = aggregate_results(comparisons)
    
    # Display results
    display_summary(summary)
    
    # Save results
    if output_file:
        save_results(summary, output_file)
    
    return summary


def aggregate_results(comparisons: List[E2ModelComparison]) -> E2ExperimentSummary:
    """Aggregate results across all models."""
    
    aggregate: Dict[ApproachType, Dict[str, List[float]]] = {
        at: {"f1_states": [], "disjoint_rate": [], "iterations": []}
        for at in ApproachType
    }
    
    for comp in comparisons:
        for approach_type, metrics in comp.metrics.items():
            aggregate[approach_type]["f1_states"].append(metrics["f1_states"])
            aggregate[approach_type]["disjoint_rate"].append(metrics["disjointness_rate"])
            aggregate[approach_type]["iterations"].append(metrics["iterations"])
    
    # Calculate averages
    avg_metrics: Dict[ApproachType, Dict[str, float]] = {}
    
    for approach_type, values in aggregate.items():
        avg_metrics[approach_type] = {
            "avg_f1_states": sum(values["f1_states"]) / len(values["f1_states"]) if values["f1_states"] else 0,
            "avg_disjoint_rate": sum(values["disjoint_rate"]) / len(values["disjoint_rate"]) if values["disjoint_rate"] else 0,
            "avg_iterations": sum(values["iterations"]) / len(values["iterations"]) if values["iterations"] else 0,
        }
    
    # Determine winner
    best_f1 = 0
    winner = ApproachType.S_SQUARE_BOT
    
    for approach_type, metrics in avg_metrics.items():
        # Weight: F1 * 0.5 + Disjoint * 0.5
        score = metrics["avg_f1_states"] * 0.5 + metrics["avg_disjoint_rate"] * 0.5
        if score > best_f1:
            best_f1 = score
            winner = approach_type
    
    return E2ExperimentSummary(
        comparisons=comparisons,
        aggregate_metrics=avg_metrics,
        winner=winner,
        timestamp=datetime.now().isoformat(),
    )


# ============================================================================
# Display & Output
# ============================================================================

def display_summary(summary: E2ExperimentSummary):
    """Display experiment summary in rich table."""
    
    console.print("\n[bold]📊 Aggregate Results[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Approach", style="cyan")
    table.add_column("Avg F1 States", justify="right")
    table.add_column("Avg Disjoint %", justify="right")
    table.add_column("Avg Iterations", justify="right")
    table.add_column("Score", justify="right")
    
    for approach_type, metrics in summary.aggregate_metrics.items():
        score = metrics["avg_f1_states"] * 0.5 + metrics["avg_disjoint_rate"] * 0.5
        
        is_winner = approach_type == summary.winner
        style = "bold green" if is_winner else ""
        
        table.add_row(
            ("🏆 " if is_winner else "") + approach_type.value,
            f"{metrics['avg_f1_states']:.2f}",
            f"{metrics['avg_disjoint_rate']*100:.0f}%",
            f"{metrics['avg_iterations']:.1f}",
            f"{score:.2f}",
            style=style,
        )
    
    console.print(table)
    
    console.print(f"\n[bold green]🏆 Winner: {summary.winner.value}[/bold green]")
    
    # Per-model details
    console.print("\n[bold]📋 Per-Model Details[/bold]\n")
    
    for comp in summary.comparisons:
        console.print(f"[bold]{comp.model_name}[/bold]: {comp.description[:50]}...")
        
        for approach_type, metrics in comp.metrics.items():
            status = "✅" if metrics["disjointness_pass"] else "❌"
            console.print(
                f"  {approach_type.value}: "
                f"F1={metrics['f1_states']:.2f}, "
                f"Disjoint={status} ({metrics['disjointness_rate']*100:.0f}%), "
                f"Iters={metrics['iterations']}"
            )
        console.print()


def save_results(summary: E2ExperimentSummary, output_file: Path):
    """Save results to JSON file."""
    
    output_data = {
        "timestamp": summary.timestamp,
        "winner": summary.winner.value,
        "aggregate_metrics": {
            at.value: metrics for at, metrics in summary.aggregate_metrics.items()
        },
        "comparisons": [
            {
                "model_name": comp.model_name,
                "description": comp.description,
                "metrics": {
                    at.value: m for at, m in comp.metrics.items()
                }
            }
            for comp in summary.comparisons
        ]
    }
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)
    
    console.print(f"\n[dim]Results saved to: {output_file}[/dim]")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main entry point."""
    output_path = project_root / "experiments" / "output" / "e2_results.json"
    
    await run_e2_experiment(output_file=output_path)


if __name__ == "__main__":
    asyncio.run(main())
