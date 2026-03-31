"""
E3 Experiment: Robustness to Noise in Requirements

This experiment tests MAS-LLM's ability to handle noisy/ambiguous requirements
by comparing results across three noise levels: clean, slight, and heavy.

Metrics:
- F1_states/transitions: F1 scores across noise levels
- F1 Drop: Decrease in F1 from clean to noisy (threshold ≤ 15 p.p.)
- Halluc_rate: Hallucination rate (threshold ≤ 5% for clean/slight)
- Clarif_rounds: Number of clarification rounds (threshold ≤ 3 average)

Usage:
    python experiments/e3_noise_robustness.py [--test-case NAME] [--verbose]
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.evaluation.metrics import (
    evaluate_model, 
    EvaluationMetrics,
    calculate_hallucination_rate,
)
from src.evaluation.reference_models import (
    load_noise_variants, 
    NoiseTestCase, 
    NoiseLevel,
    NoiseVariant,
)

# Import workflow for pipeline execution
from src.orchestration.langgraph_workflow import SquareIDEWorkflow

from dotenv import load_dotenv

load_dotenv()

console = Console()


@dataclass
class NoiseVariantResult:
    """Result for a single noise variant."""
    noise_level: str
    f1_states: float
    f1_transitions: float
    hallucination_rate: float
    clarification_rounds: int
    generated_states_count: int
    generated_transitions_count: int
    processing_time_ms: int
    error: Optional[str] = None


@dataclass 
class E3TestCaseResult:
    """Result for a complete test case (all noise variants)."""
    test_case_name: str
    variants: Dict[str, NoiseVariantResult]
    
    # Computed metrics
    f1_states_drop_slight: float  # Clean - Slight
    f1_states_drop_heavy: float   # Clean - Heavy
    f1_transitions_drop_slight: float
    f1_transitions_drop_heavy: float
    
    # Thresholds check
    meets_f1_drop_threshold: bool  # ≤ 15 p.p. for heavy
    meets_halluc_threshold_clean: bool  # ≤ 5%
    meets_halluc_threshold_slight: bool  # ≤ 5%
    meets_clarif_threshold: bool  # ≤ 3 average
    
    overall_success: bool
    timestamp: str


@dataclass
class E3ExperimentSummary:
    """Summary of all E3 experiment runs."""
    total_test_cases: int
    successful_test_cases: int
    average_f1_drop_heavy_states: float
    average_f1_drop_heavy_transitions: float
    average_halluc_rate_clean: float
    average_halluc_rate_slight: float
    average_halluc_rate_heavy: float
    average_clarif_rounds: float
    results: List[Dict[str, Any]]
    timestamp: str


async def run_pipeline_with_tracking(requirements: str) -> Dict[str, Any]:
    """
    Run the pipeline using SquareIDEWorkflow and track clarification rounds.
    
    Returns dict with pipeline results including clarification_rounds.
    """
    workflow = SquareIDEWorkflow()
    
    try:
        final_state = await workflow.run(requirements)
        
        return {
            "success": True,
            "state_machine": final_state.get("state_machine", {}),
            "logic_model": final_state.get("logic_model", {}),
            "ontology_model": final_state.get("ontology_model", {}),
            "verification_results": final_state.get("verification_results", []),
            "clarification_rounds": final_state.get("clarification_rounds", 0),
            "clarifications_needed": final_state.get("clarifications_needed", []),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "state_machine": {},
            "clarification_rounds": 0,
        }


async def run_single_variant(
    variant: NoiseVariant,
    reference_sm: Dict[str, Any],
    verbose: bool = False
) -> NoiseVariantResult:
    """Run experiment on a single noise variant."""
    
    start_time = datetime.now()
    
    if verbose:
        console.print(f"  [dim]Running {variant.noise_level.value} variant...[/dim]")
    
    try:
        # Run pipeline
        result = await run_pipeline_with_tracking(variant.requirements)
        
        if not result["success"]:
            raise RuntimeError(result.get("error", "Pipeline failed"))
        
        generated_sm = result["state_machine"]
        verification_results = result.get("verification_results", [])
        
        # Build verification report from results
        verification_report = {}
        if verification_results:
            latest = verification_results[-1]
            verification_report = {
                "issues": latest.get("issues", []),
                "statistics": {
                    "total_issues": len(latest.get("issues", [])),
                    "errors": sum(1 for i in latest.get("issues", []) if i.get("severity") == "error"),
                }
            }
        
        # Calculate metrics
        metrics = evaluate_model(
            generated=generated_sm,
            reference=reference_sm,
            verification_report=verification_report
        )
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return NoiseVariantResult(
            noise_level=variant.noise_level.value,
            f1_states=metrics.f1_states,
            f1_transitions=metrics.f1_transitions,
            hallucination_rate=metrics.hallucination_rate,
            clarification_rounds=result.get("clarification_rounds", 0),
            generated_states_count=metrics.generated_states_count,
            generated_transitions_count=metrics.generated_transitions_count,
            processing_time_ms=processing_time,
        )
        
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return NoiseVariantResult(
            noise_level=variant.noise_level.value,
            f1_states=0.0,
            f1_transitions=0.0,
            hallucination_rate=1.0,
            clarification_rounds=0,
            generated_states_count=0,
            generated_transitions_count=0,
            processing_time_ms=processing_time,
            error=str(e),
        )


async def run_test_case(
    test_case: NoiseTestCase,
    verbose: bool = False
) -> E3TestCaseResult:
    """Run E3 experiment on a complete test case with all noise variants."""
    
    if verbose:
        console.print(f"\n[bold cyan]Test Case: {test_case.name}[/bold cyan]")
    
    # Get reference state machine
    reference_sm = test_case.reference_model.to_state_machine_dict()
    
    # Run all variants
    variants: Dict[str, NoiseVariantResult] = {}
    
    for level in [NoiseLevel.CLEAN, NoiseLevel.SLIGHT, NoiseLevel.HEAVY]:
        variant = test_case.variants.get(level)
        if variant:
            result = await run_single_variant(variant, reference_sm, verbose)
            variants[level.value] = result
    
    # Calculate F1 drops
    clean = variants.get("clean")
    slight = variants.get("slight")
    heavy = variants.get("heavy")
    
    if clean and slight:
        f1_states_drop_slight = clean.f1_states - slight.f1_states
        f1_trans_drop_slight = clean.f1_transitions - slight.f1_transitions
    else:
        f1_states_drop_slight = f1_trans_drop_slight = 0.0
    
    if clean and heavy:
        f1_states_drop_heavy = clean.f1_states - heavy.f1_states
        f1_trans_drop_heavy = clean.f1_transitions - heavy.f1_transitions
    else:
        f1_states_drop_heavy = f1_trans_drop_heavy = 0.0
    
    # Check thresholds
    meets_f1_drop = (
        f1_states_drop_heavy <= 0.15 and 
        f1_trans_drop_heavy <= 0.15
    )
    
    meets_halluc_clean = clean.hallucination_rate <= 0.05 if clean else False
    meets_halluc_slight = slight.hallucination_rate <= 0.05 if slight else False
    
    # Average clarification rounds
    all_clarif = [v.clarification_rounds for v in variants.values() if not v.error]
    avg_clarif = sum(all_clarif) / len(all_clarif) if all_clarif else 0
    meets_clarif = avg_clarif <= 3
    
    overall_success = (
        meets_f1_drop and 
        meets_halluc_clean and 
        meets_halluc_slight and
        meets_clarif
    )
    
    result = E3TestCaseResult(
        test_case_name=test_case.name,
        variants={k: asdict(v) for k, v in variants.items()},
        f1_states_drop_slight=f1_states_drop_slight,
        f1_states_drop_heavy=f1_states_drop_heavy,
        f1_transitions_drop_slight=f1_trans_drop_slight,
        f1_transitions_drop_heavy=f1_trans_drop_heavy,
        meets_f1_drop_threshold=meets_f1_drop,
        meets_halluc_threshold_clean=meets_halluc_clean,
        meets_halluc_threshold_slight=meets_halluc_slight,
        meets_clarif_threshold=meets_clarif,
        overall_success=overall_success,
        timestamp=datetime.now().isoformat(),
    )
    
    if verbose:
        _display_test_case_result(result)
    
    return result


def _display_test_case_result(result: E3TestCaseResult) -> None:
    """Display result for a single test case."""
    
    # Variants table
    table = Table(title=f"Results: {result.test_case_name}", box=box.ROUNDED)
    table.add_column("Noise Level", style="cyan")
    table.add_column("F1 States", style="white")
    table.add_column("F1 Trans", style="white")
    table.add_column("Halluc %", style="white")
    table.add_column("Clarif", style="white")
    table.add_column("Status", style="white")
    
    for level in ["clean", "slight", "heavy"]:
        v = result.variants.get(level)
        if v:
            status = "✅" if not v.get("error") else f"❌ {v.get('error', '')[:20]}"
            table.add_row(
                level.upper(),
                f"{v.get('f1_states', 0):.3f}",
                f"{v.get('f1_transitions', 0):.3f}",
                f"{v.get('hallucination_rate', 0):.1%}",
                str(v.get('clarification_rounds', 0)),
                status
            )
    
    console.print(table)
    
    # F1 Drop summary
    console.print(f"  F1 Drop (heavy): states={result.f1_states_drop_heavy:.3f}, "
                  f"transitions={result.f1_transitions_drop_heavy:.3f} "
                  f"[{'✅' if result.meets_f1_drop_threshold else '❌'} ≤0.15]")
    
    console.print(f"  Hallucination: clean={'✅' if result.meets_halluc_threshold_clean else '❌'}, "
                  f"slight={'✅' if result.meets_halluc_threshold_slight else '❌'} [≤5%]")
    
    console.print(f"  Clarification: {'✅' if result.meets_clarif_threshold else '❌'} [avg ≤3]")
    
    status = "[bold green]SUCCESS[/bold green]" if result.overall_success else "[bold red]FAILED[/bold red]"
    console.print(f"  Overall: {status}\n")


async def run_e3_experiment(
    test_case_names: Optional[List[str]] = None,
    verbose: bool = True,
    save_results: bool = True
) -> E3ExperimentSummary:
    """
    Run E3 experiment on all or selected test cases.
    
    Args:
        test_case_names: Optional list of test case names. If None, tests all.
        verbose: If True, display detailed output.
        save_results: If True, save results to JSON file.
        
    Returns:
        E3ExperimentSummary with all results
    """
    
    console.print(Panel.fit(
        "[bold]E3 Experiment: Robustness to Noise[/bold]\n"
        "Testing MAS-LLM with clean, slightly noisy, and heavily noisy requirements",
        title="🔬 Experiment E3",
        border_style="green"
    ))
    
    # Load test cases
    test_cases = load_noise_variants()
    
    # Filter by names if specified
    if test_case_names:
        test_cases = [tc for tc in test_cases if tc.name in test_case_names]
    
    if not test_cases:
        console.print("[bold red]No test cases found![/bold red]")
        return None
    
    console.print(f"[dim]Testing {len(test_cases)} case(s) × 3 variants = {len(test_cases) * 3} runs...[/dim]\n")
    
    # Run experiments
    results: List[E3TestCaseResult] = []
    for test_case in test_cases:
        result = await run_test_case(test_case, verbose=verbose)
        results.append(result)
    
    # Calculate summary
    successful = [r for r in results if r.overall_success]
    
    # Aggregate metrics
    all_clean_halluc = [r.variants.get("clean", {}).get("hallucination_rate", 0) for r in results]
    all_slight_halluc = [r.variants.get("slight", {}).get("hallucination_rate", 0) for r in results]
    all_heavy_halluc = [r.variants.get("heavy", {}).get("hallucination_rate", 0) for r in results]
    
    all_clarif = []
    for r in results:
        for v in r.variants.values():
            if not v.get("error"):
                all_clarif.append(v.get("clarification_rounds", 0))
    
    summary = E3ExperimentSummary(
        total_test_cases=len(results),
        successful_test_cases=len(successful),
        average_f1_drop_heavy_states=sum(r.f1_states_drop_heavy for r in results) / len(results) if results else 0,
        average_f1_drop_heavy_transitions=sum(r.f1_transitions_drop_heavy for r in results) / len(results) if results else 0,
        average_halluc_rate_clean=sum(all_clean_halluc) / len(all_clean_halluc) if all_clean_halluc else 0,
        average_halluc_rate_slight=sum(all_slight_halluc) / len(all_slight_halluc) if all_slight_halluc else 0,
        average_halluc_rate_heavy=sum(all_heavy_halluc) / len(all_heavy_halluc) if all_heavy_halluc else 0,
        average_clarif_rounds=sum(all_clarif) / len(all_clarif) if all_clarif else 0,
        results=[asdict(r) for r in results],
        timestamp=datetime.now().isoformat(),
    )
    
    # Display summary
    _display_summary(summary)
    
    # Save results
    if save_results:
        output_path = Path(__file__).parent / "output" / "e3_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, indent=2, ensure_ascii=False)
        
        console.print(f"\n[dim]Results saved to: {output_path}[/dim]")
    
    return summary


def _display_summary(summary: E3ExperimentSummary) -> None:
    """Display experiment summary."""
    
    console.print("\n")
    console.rule("[bold]E3 Experiment Summary[/bold]")
    
    # Summary table
    table = Table(box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_column("Threshold", style="yellow")
    table.add_column("Status", style="white")
    
    # F1 Drop
    f1_drop_ok = summary.average_f1_drop_heavy_states <= 0.15 and summary.average_f1_drop_heavy_transitions <= 0.15
    table.add_row(
        "Avg F1 Drop (heavy)",
        f"S: {summary.average_f1_drop_heavy_states:.3f}, T: {summary.average_f1_drop_heavy_transitions:.3f}",
        "≤ 0.15 (15 p.p.)",
        "✅" if f1_drop_ok else "❌"
    )
    
    # Hallucination rates
    table.add_row(
        "Halluc Rate (clean)",
        f"{summary.average_halluc_rate_clean:.1%}",
        "≤ 5%",
        "✅" if summary.average_halluc_rate_clean <= 0.05 else "❌"
    )
    table.add_row(
        "Halluc Rate (slight)",
        f"{summary.average_halluc_rate_slight:.1%}",
        "≤ 5%",
        "✅" if summary.average_halluc_rate_slight <= 0.05 else "❌"
    )
    table.add_row(
        "Halluc Rate (heavy)",
        f"{summary.average_halluc_rate_heavy:.1%}",
        "(no threshold)",
        "-"
    )
    
    # Clarification rounds
    table.add_row(
        "Avg Clarif Rounds",
        f"{summary.average_clarif_rounds:.1f}",
        "≤ 3",
        "✅" if summary.average_clarif_rounds <= 3 else "❌"
    )
    
    console.print(table)
    
    # Overall stats
    success_rate = summary.successful_test_cases / summary.total_test_cases if summary.total_test_cases > 0 else 0
    console.print(f"\n[bold]Test Cases:[/bold] {summary.successful_test_cases}/{summary.total_test_cases} passed ({success_rate:.0%})")
    
    if summary.successful_test_cases == summary.total_test_cases:
        console.print("[bold green]🎉 All thresholds met! Experiment PASSED.[/bold green]")
    else:
        failed = summary.total_test_cases - summary.successful_test_cases
        console.print(f"[bold yellow]⚠️ {failed} test case(s) failed to meet thresholds.[/bold yellow]")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run E3 Noise Robustness Experiment")
    parser.add_argument("--test-case", "-t", type=str, help="Specific test case name to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to file")
    
    args = parser.parse_args()
    
    test_case_names = [args.test_case] if args.test_case else None
    
    asyncio.run(run_e3_experiment(
        test_case_names=test_case_names,
        verbose=args.verbose or True,
        save_results=not args.no_save
    ))
