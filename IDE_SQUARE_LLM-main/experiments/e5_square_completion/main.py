"""
E5 Square Completion Accuracy Experiment - Main Runner

Tests the accuracy of Square of Opposition inference with partial input.

Scenarios:
- C1: 1 corner given -> infer 3
- C2: 2 corners given -> infer 2
- C3: 3 corners given -> infer 1

Usage:
    python -m experiments.e5_square_completion
    python experiments/e5_square_completion/main.py
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import asdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from dotenv import load_dotenv

load_dotenv()

from src.agents.llm_agent import LLMAgent

from .models import (
    CornerType,
    ScenarioType,
    SquareRelation,
    E5InferenceResult,
    E5ScenarioResult,
    E5StateMachineImpact,
    E5ExperimentSummary,
)
from .corner_scenarios import (
    generate_all_test_cases,
    SQUARE_TEST_CASES,
)

console = Console()


# ============================================================================
# Square Completion Inference
# ============================================================================

async def infer_square_completion(
    given_relations: List[SquareRelation],
    subject: str,
    predicate: str,
) -> Dict[str, SquareRelation]:
    """
    Use LLM to infer missing corners of the Square of Opposition.
    
    Args:
        given_relations: List of known relations
        subject: Subject term (S)
        predicate: Predicate term (P)
    
    Returns:
        Dict mapping corner type to inferred relation
    """
    llm_agent = LLMAgent()
    
    # Build input for inference
    if len(given_relations) == 1:
        rel = given_relations[0]
        input_data = {
            "relation": {
                "type": rel.corner.value,
                "subject": subject,
                "predicate": predicate,
                "status": rel.status,
            }
        }
        
        result = await llm_agent.execute({
            "task_type": "infer_logic_square",
            **input_data
        })
        
        if result.get("success") and result.get("result"):
            inferred = result["result"].get("inferred_relations", [])
            
            if inferred:
                return _parse_inferred_relations(inferred, subject, predicate)
    
    # For 2+ corners, use custom prompt
    return await _infer_multiple_corners(llm_agent, given_relations, subject, predicate)


async def _infer_multiple_corners(
    llm_agent: LLMAgent,
    given_relations: List[SquareRelation],
    subject: str,
    predicate: str,
) -> Dict[str, SquareRelation]:
    """Infer from multiple given corners."""
    
    # Build description of given relations
    given_desc = "\n".join([
        f"- {rel.corner.name} ({rel.corner.value}): {rel.statement} -> {rel.status}"
        for rel in given_relations
    ])
    
    given_corners = {rel.corner for rel in given_relations}
    missing_corners = [c for c in CornerType if c not in given_corners]
    
    prompt = f"""
    Given the following Square of Opposition relations for S="{subject}" and P="{predicate}":
    
    {given_desc}
    
    Using classical Square of Opposition logic, infer the status of the remaining relations:
    {', '.join([c.name for c in missing_corners])}
    
    For each missing relation, provide:
    - "square_label": A | E | I | O
    - "status": TRUE | FALSE | UNDETERMINED
    - "statement": the formal logical sentence
    
    Respond with JSON:
    {{
        "inferred_relations": [
            {{"square_label": "X", "status": "...", "statement": "..."}}
        ]
    }}
    """
    
    try:
        response = llm_agent.client.chat.completions.create(
            model=llm_agent.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.05,
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        parsed = json.loads(result_text)
        inferred = parsed.get("inferred_relations", [])
        
        return _parse_inferred_relations(inferred, subject, predicate)
        
    except Exception:
        return {}


def _parse_inferred_relations(
    inferred: List[Dict[str, Any]],
    subject: str,
    predicate: str,
) -> Dict[str, SquareRelation]:
    """Parse inferred relations from LLM response."""
    result = {}
    
    label_to_corner = {
        "A": CornerType.A,
        "E": CornerType.E,
        "I": CornerType.I,
        "O": CornerType.O,
    }
    
    type_to_corner = {
        "universal_affirmative": CornerType.A,
        "universal_negative": CornerType.E,
        "particular_affirmative": CornerType.I,
        "particular_negative": CornerType.O,
    }
    
    for rel in inferred:
        # Get corner type from label or type field
        corner = None
        if "square_label" in rel:
            corner = label_to_corner.get(rel["square_label"])
        elif "type" in rel:
            corner = type_to_corner.get(rel["type"])
        
        if corner:
            result[corner.value] = SquareRelation(
                corner=corner,
                subject=subject,
                predicate=predicate,
                status=rel.get("status", "UNDETERMINED"),
                statement=rel.get("statement", ""),
                natural_language=rel.get("natural_language", ""),
            )
    
    return result


# ============================================================================
# Test Case Execution
# ============================================================================

async def run_single_test(test_case: Dict[str, Any]) -> E5InferenceResult:
    """Run a single inference test case."""
    
    start_time = datetime.now()
    
    try:
        # Run inference
        inferred = await infer_square_completion(
            given_relations=test_case["given_relations"],
            subject=test_case["subject"],
            predicate=test_case["predicate"],
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Calculate accuracy
        expected = test_case["expected_inferences"]
        correct_relations = 0
        correct_statuses = 0
        total = len(expected)
        
        for corner_type, expected_rel in expected.items():
            if corner_type in inferred:
                actual = inferred[corner_type]
                
                # Check if status matches
                if actual.status.upper() == expected_rel.status.upper():
                    correct_statuses += 1
                    correct_relations += 1
        
        # Determine scenario type from number of given corners
        num_given = len(test_case["given_corners"])
        scenario_type = {
            1: ScenarioType.C1_ONE_CORNER,
            2: ScenarioType.C2_TWO_CORNERS,
            3: ScenarioType.C3_THREE_CORNERS,
        }.get(num_given, ScenarioType.C1_ONE_CORNER)
        
        # Convert expected to serializable format
        expected_dict = {}
        for k, v in expected.items():
            expected_dict[k] = v
        
        return E5InferenceResult(
            scenario_type=scenario_type,
            test_case_name=test_case["test_case_name"],
            given_corners=test_case["given_corners"],
            expected_inferences=expected_dict,
            actual_inferences=inferred,
            correct_relations=correct_relations,
            total_relations=total,
            correct_statuses=correct_statuses,
            execution_time=elapsed,
        )
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        
        num_given = len(test_case["given_corners"])
        scenario_type = {
            1: ScenarioType.C1_ONE_CORNER,
            2: ScenarioType.C2_TWO_CORNERS,
            3: ScenarioType.C3_THREE_CORNERS,
        }.get(num_given, ScenarioType.C1_ONE_CORNER)
        
        return E5InferenceResult(
            scenario_type=scenario_type,
            test_case_name=test_case["test_case_name"],
            given_corners=test_case["given_corners"],
            expected_inferences={},
            actual_inferences={},
            execution_time=elapsed,
            error=str(e),
        )


async def run_scenario(
    scenario_type: ScenarioType,
    test_cases: List[Dict[str, Any]],
    verbose: bool = False,
) -> E5ScenarioResult:
    """Run all test cases for a scenario type."""
    
    if verbose:
        console.print(f"\n[bold cyan]Running {scenario_type.value}...[/bold cyan]")
    
    results: List[E5InferenceResult] = []
    
    for i, test_case in enumerate(test_cases):
        if verbose:
            console.print(f"  [dim]{i+1}/{len(test_cases)}: {test_case['test_case_name']}[/dim]")
        
        result = await run_single_test(test_case)
        results.append(result)
    
    # Aggregate metrics
    total_correct = sum(r.correct_relations for r in results)
    total_inferences = sum(r.total_relations for r in results)
    total_correct_status = sum(r.correct_statuses for r in results)
    
    avg_relation_accuracy = total_correct / total_inferences if total_inferences > 0 else 0
    avg_status_accuracy = total_correct_status / total_inferences if total_inferences > 0 else 0
    
    return E5ScenarioResult(
        scenario_type=scenario_type,
        test_cases=results,
        avg_relation_accuracy=avg_relation_accuracy,
        avg_status_accuracy=avg_status_accuracy,
        total_correct=total_correct,
        total_inferences=total_inferences,
    )


# ============================================================================
# Experiment Runner
# ============================================================================

async def run_e5_experiment(
    scenarios: List[ScenarioType] = None,
    verbose: bool = True,
    output_file: Path = None,
) -> E5ExperimentSummary:
    """
    Run the full E5 square completion experiment.
    
    Args:
        scenarios: List of scenarios to run. If None, runs all.
        verbose: If True, display detailed output.
        output_file: Optional path to save results JSON.
    
    Returns:
        E5ExperimentSummary with all results
    """
    console.print(Panel.fit(
        "[bold cyan]E5 Experiment: Square Completion Accuracy[/bold cyan]\n"
        "Testing inference from 1, 2, or 3 given corners",
        border_style="green"
    ))
    
    # Generate all test cases
    all_cases = generate_all_test_cases()
    
    if scenarios is None:
        scenarios = list(ScenarioType)
    
    # Map scenario type to case key
    scenario_to_key = {
        ScenarioType.C1_ONE_CORNER: "C1_one_corner",
        ScenarioType.C2_TWO_CORNERS: "C2_two_corners",
        ScenarioType.C3_THREE_CORNERS: "C3_three_corners",
    }
    
    scenario_results: Dict[ScenarioType, E5ScenarioResult] = {}
    
    for scenario_type in scenarios:
        key = scenario_to_key[scenario_type]
        cases = all_cases.get(key, [])
        
        console.print(f"\n[bold]📋 {scenario_type.value}: {len(cases)} test cases[/bold]")
        
        result = await run_scenario(scenario_type, cases, verbose)
        scenario_results[scenario_type] = result
    
    # Calculate accuracy by corners
    accuracy_by_corners = {}
    for scenario_type, result in scenario_results.items():
        num_corners = {
            ScenarioType.C1_ONE_CORNER: 1,
            ScenarioType.C2_TWO_CORNERS: 2,
            ScenarioType.C3_THREE_CORNERS: 3,
        }.get(scenario_type, 1)
        accuracy_by_corners[num_corners] = result.avg_relation_accuracy
    
    summary = E5ExperimentSummary(
        scenario_results=scenario_results,
        sm_impact={},  # State machine impact would require additional pipeline runs
        accuracy_by_corners=accuracy_by_corners,
        timestamp=datetime.now().isoformat(),
    )
    
    # Display results
    display_summary(summary)
    
    # Save results
    if output_file:
        save_results(summary, output_file)
    
    return summary


# ============================================================================
# Display & Output
# ============================================================================

def display_summary(summary: E5ExperimentSummary):
    """Display experiment summary in rich table."""
    
    console.print("\n[bold]📊 Results by Scenario[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Scenario", style="cyan")
    table.add_column("Corners Given", justify="center")
    table.add_column("Test Cases", justify="right")
    table.add_column("Relation Accuracy", justify="right")
    table.add_column("Status Accuracy", justify="right")
    
    for scenario_type, result in summary.scenario_results.items():
        num_corners = {
            ScenarioType.C1_ONE_CORNER: 1,
            ScenarioType.C2_TWO_CORNERS: 2,
            ScenarioType.C3_THREE_CORNERS: 3,
        }.get(scenario_type, 1)
        
        accuracy_style = "green" if result.avg_relation_accuracy >= 0.8 else (
            "yellow" if result.avg_relation_accuracy >= 0.5 else "red"
        )
        
        table.add_row(
            scenario_type.value,
            str(num_corners),
            str(len(result.test_cases)),
            f"[{accuracy_style}]{result.avg_relation_accuracy:.1%}[/{accuracy_style}]",
            f"{result.avg_status_accuracy:.1%}",
        )
    
    console.print(table)
    
    # Accuracy trend
    console.print("\n[bold]📈 Accuracy Trend (more corners → expected higher accuracy)[/bold]\n")
    
    for corners, accuracy in sorted(summary.accuracy_by_corners.items()):
        bar_len = int(accuracy * 40)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        console.print(f"  {corners} corner(s): [{bar}] {accuracy:.1%}")


def save_results(summary: E5ExperimentSummary, output_file: Path):
    """Save results to JSON file."""
    
    # Convert to serializable format
    output_data = {
        "timestamp": summary.timestamp,
        "accuracy_by_corners": summary.accuracy_by_corners,
        "scenario_results": {}
    }
    
    for scenario_type, result in summary.scenario_results.items():
        output_data["scenario_results"][scenario_type.value] = {
            "avg_relation_accuracy": result.avg_relation_accuracy,
            "avg_status_accuracy": result.avg_status_accuracy,
            "total_correct": result.total_correct,
            "total_inferences": result.total_inferences,
            "test_cases_count": len(result.test_cases),
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
    
    parser = argparse.ArgumentParser(description="Run E5 Square Completion Experiment")
    parser.add_argument("--scenario", "-s", type=str, 
                       choices=["C1", "C2", "C3"],
                       help="Specific scenario to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    output_path = project_root / "experiments" / "output" / "e5_results.json"
    
    scenarios = None
    if args.scenario:
        scenario_map = {
            "C1": ScenarioType.C1_ONE_CORNER,
            "C2": ScenarioType.C2_TWO_CORNERS,
            "C3": ScenarioType.C3_THREE_CORNERS,
        }
        scenarios = [scenario_map[args.scenario]]
    
    await run_e5_experiment(
        scenarios=scenarios,
        verbose=args.verbose or True,
        output_file=output_path,
    )


if __name__ == "__main__":
    asyncio.run(main())
