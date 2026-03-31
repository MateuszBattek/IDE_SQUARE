"""
E4 Algorithm Ablation Experiment - Main Runner

Compares system performance with different components disabled:
- V1: Full system (baseline)
- V2: Without prover (no Z3)
- V3: Without verifier
- V4: Without square completion

Usage:
    python -m experiments.e4_algorithm_ablation
    python experiments/e4_algorithm_ablation/main.py
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import statistics

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from dotenv import load_dotenv

load_dotenv()

from src.evaluation.metrics import calculate_f1_states, calculate_f1_transitions

from .models import (
    AblationVariant as AblationVariantEnum,
    E4VariantResult,
    E4StabilityResult,
    E4ModelComparison,
    E4ExperimentSummary,
)
from .variants import (
    FullSystemVariant,
    NoProverVariant,
    NoVerifierVariant,
    NoSquareCompletionVariant,
)

console = Console()

STABILITY_RUNS = 3  # Number of runs for stability measurement


# ============================================================================
# Reference Models Loader
# ============================================================================

def load_reference_models() -> Dict[str, Dict[str, Any]]:
    """Load reference models from test data."""
    ref_path = project_root / "experiments" / "test_data" / "e1_reference_models.json"
    
    if ref_path.exists():
        with open(ref_path) as f:
            data = json.load(f)
        
        if "reference_models" in data:
            models = {}
            for model in data["reference_models"]:
                name = model["name"]
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
    
    console.print("[yellow]⚠ Reference models not found, using minimal set[/yellow]")
    return {
        "order_lifecycle": {
            "description": "Order processing lifecycle",
            "requirements": "Order processing system: All new orders are pending. All pending orders can become processing.",
            "expected_states": ["pending", "processing", "completed", "cancelled"],
            "expected_transitions": 4
        }
    }


# ============================================================================
# Variant Execution
# ============================================================================

def get_variant_class(variant_type: AblationVariantEnum):
    """Get the variant class for a given type."""
    mapping = {
        AblationVariantEnum.V1_FULL: FullSystemVariant,
        AblationVariantEnum.V2_NO_PROVER: NoProverVariant,
        AblationVariantEnum.V3_NO_VERIFIER: NoVerifierVariant,
        AblationVariantEnum.V4_NO_SQUARE: NoSquareCompletionVariant,
    }
    return mapping[variant_type]


async def run_variant(
    variant_type: AblationVariantEnum,
    requirements: str,
    model_name: str,
) -> E4VariantResult:
    """Run a single ablation variant and return results."""
    console.print(f"  [dim]Running {variant_type.value}...[/dim]")
    
    start_time = datetime.now()
    
    try:
        variant_class = get_variant_class(variant_type)
        variant = variant_class()
        
        state_machine, iterations = await variant.generate(requirements)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        metrics = variant.get_metrics()
        
        return E4VariantResult(
            variant=variant_type,
            model_name=model_name,
            generated_machine=state_machine,
            iterations=iterations,
            execution_time=elapsed,
            contradictions_count=metrics["contradictions_count"],
            models_rejected=metrics["models_rejected"],
            prover_calls=metrics["prover_calls"],
            verifier_calls=metrics["verifier_calls"],
            error=state_machine.get("error"),
        )
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        return E4VariantResult(
            variant=variant_type,
            model_name=model_name,
            generated_machine={"states": [], "transitions": []},
            iterations=0,
            execution_time=elapsed,
            error=str(e),
        )


async def run_stability_test(
    variant_type: AblationVariantEnum,
    requirements: str,
    model_name: str,
    expected_states: set,
) -> E4StabilityResult:
    """Run multiple iterations to measure stability."""
    f1_scores = []
    
    for run in range(STABILITY_RUNS):
        result = await run_variant(variant_type, requirements, model_name)
        
        # Calculate F1 for this run
        generated_states = set(
            s.get("name", "").lower() for s in result.generated_machine.get("states", [])
        )
        
        if len(expected_states) > 0 or len(generated_states) > 0:
            precision = (
                len(expected_states & generated_states) / len(generated_states)
                if generated_states else 0
            )
            recall = (
                len(expected_states & generated_states) / len(expected_states)
                if expected_states else 0
            )
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0 else 0
            )
        else:
            f1 = 0.0
        
        f1_scores.append(f1)
    
    f1_mean = statistics.mean(f1_scores)
    f1_std = statistics.stdev(f1_scores) if len(f1_scores) > 1 else 0.0
    
    return E4StabilityResult(
        variant=variant_type,
        model_name=model_name,
        f1_scores=f1_scores,
        f1_mean=f1_mean,
        f1_std=f1_std,
        is_stable=f1_std <= 0.05,
    )


async def compare_variants(
    model_name: str,
    model_data: Dict[str, Any],
    run_stability: bool = False,
) -> E4ModelComparison:
    """Compare all ablation variants on a single model."""
    requirements = model_data["requirements"]
    expected_states = set(s.lower() for s in model_data["expected_states"])
    
    results: Dict[AblationVariantEnum, E4VariantResult] = {}
    stability: Dict[AblationVariantEnum, E4StabilityResult] = {}
    metrics: Dict[AblationVariantEnum, Dict[str, Any]] = {}
    
    for variant_type in AblationVariantEnum:
        # Single run
        result = await run_variant(variant_type, requirements, model_name)
        results[variant_type] = result
        
        # Calculate metrics
        generated_states = set(
            s.get("name", "").lower() for s in result.generated_machine.get("states", [])
        )
        
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
        
        metrics[variant_type] = {
            "f1_states": f1_states,
            "contradictions": result.contradictions_count,
            "models_rejected": result.models_rejected,
            "iterations": result.iterations,
            "prover_calls": result.prover_calls,
            "verifier_calls": result.verifier_calls,
        }
        
        # Stability test (optional)
        if run_stability:
            stability_result = await run_stability_test(
                variant_type, requirements, model_name, expected_states
            )
            stability[variant_type] = stability_result
    
    return E4ModelComparison(
        model_name=model_name,
        description=model_data.get("description", ""),
        results=results,
        stability=stability,
        metrics=metrics,
    )


# ============================================================================
# Experiment Runner
# ============================================================================

async def run_e4_experiment(
    models: Dict[str, Dict[str, Any]] = None,
    run_stability: bool = False,
    output_file: Path = None,
) -> E4ExperimentSummary:
    """
    Run the full E4 ablation experiment.
    
    Args:
        models: Optional custom models dict. If None, loads reference models.
        run_stability: If True, run stability tests (3 runs per variant).
        output_file: Optional path to save results JSON.
    
    Returns:
        E4ExperimentSummary with all results
    """
    console.print(Panel.fit(
        "[bold cyan]E4 Experiment: Algorithm Ablation Study[/bold cyan]\n"
        "Comparing V1 (Full), V2 (No Prover), V3 (No Verifier), V4 (No Square)",
        border_style="cyan"
    ))
    
    if models is None:
        models = load_reference_models()
    
    console.print(f"\n[bold]Testing {len(models)} models...[/bold]\n")
    
    comparisons: List[E4ModelComparison] = []
    
    for model_name, model_data in models.items():
        console.print(f"[bold blue]📋 {model_name}[/bold blue]")
        comparison = await compare_variants(model_name, model_data, run_stability)
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


def aggregate_results(comparisons: List[E4ModelComparison]) -> E4ExperimentSummary:
    """Aggregate results across all models."""
    
    aggregate: Dict[AblationVariantEnum, Dict[str, List[float]]] = {
        vt: {
            "f1_states": [], 
            "contradictions": [], 
            "models_rejected": [],
            "iterations": [],
        }
        for vt in AblationVariantEnum
    }
    
    for comp in comparisons:
        for variant_type, metrics in comp.metrics.items():
            aggregate[variant_type]["f1_states"].append(metrics["f1_states"])
            aggregate[variant_type]["contradictions"].append(metrics["contradictions"])
            aggregate[variant_type]["models_rejected"].append(metrics["models_rejected"])
            aggregate[variant_type]["iterations"].append(metrics["iterations"])
    
    # Calculate averages
    avg_metrics: Dict[AblationVariantEnum, Dict[str, float]] = {}
    
    for variant_type, values in aggregate.items():
        avg_metrics[variant_type] = {
            "avg_f1_states": sum(values["f1_states"]) / len(values["f1_states"]) if values["f1_states"] else 0,
            "avg_contradictions": sum(values["contradictions"]) / len(values["contradictions"]) if values["contradictions"] else 0,
            "avg_models_rejected": sum(values["models_rejected"]) / len(values["models_rejected"]) if values["models_rejected"] else 0,
            "avg_iterations": sum(values["iterations"]) / len(values["iterations"]) if values["iterations"] else 0,
        }
    
    # Calculate component impact (difference from full system)
    full_f1 = avg_metrics[AblationVariantEnum.V1_FULL]["avg_f1_states"]
    component_impact = {
        "prover_impact": full_f1 - avg_metrics[AblationVariantEnum.V2_NO_PROVER]["avg_f1_states"],
        "verifier_impact": full_f1 - avg_metrics[AblationVariantEnum.V3_NO_VERIFIER]["avg_f1_states"],
        "square_completion_impact": full_f1 - avg_metrics[AblationVariantEnum.V4_NO_SQUARE]["avg_f1_states"],
    }
    
    return E4ExperimentSummary(
        comparisons=comparisons,
        aggregate_metrics=avg_metrics,
        component_impact=component_impact,
        timestamp=datetime.now().isoformat(),
    )


# ============================================================================
# Display & Output
# ============================================================================

def display_summary(summary: E4ExperimentSummary):
    """Display experiment summary in rich table."""
    
    console.print("\n[bold]📊 Aggregate Results[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Variant", style="cyan")
    table.add_column("Avg F1 States", justify="right")
    table.add_column("Avg Contradictions", justify="right")
    table.add_column("Avg Rejected", justify="right")
    table.add_column("Avg Iterations", justify="right")
    
    for variant_type, metrics in summary.aggregate_metrics.items():
        is_baseline = variant_type == AblationVariantEnum.V1_FULL
        style = "bold green" if is_baseline else ""
        
        table.add_row(
            ("⭐ " if is_baseline else "") + variant_type.value,
            f"{metrics['avg_f1_states']:.2f}",
            f"{metrics['avg_contradictions']:.1f}",
            f"{metrics['avg_models_rejected']:.1f}",
            f"{metrics['avg_iterations']:.1f}",
            style=style,
        )
    
    console.print(table)
    
    # Component impact
    console.print("\n[bold]🔧 Component Impact (F1 drop when removed)[/bold]\n")
    
    impact_table = Table(show_header=True, header_style="bold yellow")
    impact_table.add_column("Component", style="cyan")
    impact_table.add_column("F1 Impact", justify="right")
    impact_table.add_column("Significance", justify="center")
    
    for component, impact in summary.component_impact.items():
        significance = "🔴 High" if impact > 0.1 else ("🟡 Medium" if impact > 0.05 else "🟢 Low")
        impact_table.add_row(
            component.replace("_impact", "").replace("_", " ").title(),
            f"{impact:+.3f}",
            significance,
        )
    
    console.print(impact_table)


def save_results(summary: E4ExperimentSummary, output_file: Path):
    """Save results to JSON file."""
    
    output_data = {
        "timestamp": summary.timestamp,
        "component_impact": summary.component_impact,
        "aggregate_metrics": {
            vt.value: metrics for vt, metrics in summary.aggregate_metrics.items()
        },
        "comparisons": [
            {
                "model_name": comp.model_name,
                "description": comp.description,
                "metrics": {
                    vt.value: m for vt, m in comp.metrics.items()
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Run E4 Algorithm Ablation Experiment")
    parser.add_argument("--model", "-m", type=str, help="Specific model name to test")
    parser.add_argument("--stability", "-s", action="store_true", help="Run stability tests (3 runs per variant)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    output_path = project_root / "experiments" / "output" / "e4_results.json"
    
    models = None
    if args.model:
        all_models = load_reference_models()
        if args.model in all_models:
            models = {args.model: all_models[args.model]}
        else:
            console.print(f"[red]Model '{args.model}' not found[/red]")
            return
    
    await run_e4_experiment(
        models=models,
        run_stability=args.stability,
        output_file=output_path,
    )


if __name__ == "__main__":
    asyncio.run(main())
