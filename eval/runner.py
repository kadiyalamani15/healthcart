"""
HealthCart eval harness.

Runs a subset of test cases through the full agent pipeline, scores each run
against the expected minimum compliance rate, and logs results to Langfuse.

Usage:
    python -m eval.runner            # runs all 20 test cases
    python -m eval.runner --n 5      # runs first N cases
    python -m eval.runner --id tc001 # runs a single case by ID
"""

import json
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langfuse import Langfuse
from agent.graph import run_agent

CASES_PATH = Path(__file__).parent / "test_cases.json"


def load_cases(n: int = None, case_id: str = None) -> list:
    with open(CASES_PATH) as f:
        cases = json.load(f)
    if case_id:
        return [c for c in cases if c["id"] == case_id]
    return cases[:n] if n else cases


def run_eval(cases: list, langfuse: Langfuse) -> dict:
    results = []

    print(f"\nRunning {len(cases)} test case(s)...\n")

    for case in cases:
        print(f"  [{case['id']}] {case['name']} ...", end=" ", flush=True)

        try:
            result = run_agent(case["profile"])
            rate = result.get("compliance_rate", 0.0)
            allergen_rate = result.get("allergen_compliance_rate")
            expected = case["expected_min_compliance"]
            passed = rate >= expected

            results.append({
                "test_id": case["id"],
                "name": case["name"],
                "compliance_rate": round(rate, 3),
                "allergen_compliance_rate": round(allergen_rate, 3) if allergen_rate is not None else None,
                "expected_min": expected,
                "passed": passed,
                "item_count": len(result.get("shopping_list", [])),
                "error": None,
            })

            allergen_note = (
                f", allergen {allergen_rate:.0%}" if allergen_rate is not None else ""
            )
            print(f"{'PASS' if passed else 'FAIL'} ({rate:.0%} vs {expected:.0%} expected{allergen_note})")

        except Exception as exc:
            results.append({
                "test_id": case["id"],
                "name": case["name"],
                "compliance_rate": 0.0,
                "allergen_compliance_rate": None,
                "expected_min": case["expected_min_compliance"],
                "passed": False,
                "item_count": 0,
                "error": str(exc),
            })
            print(f"ERROR — {exc}")

    # Aggregate metrics
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    errors = sum(1 for r in results if r["error"])
    avg_rate = (
        sum(r["compliance_rate"] for r in results if not r["error"]) / (total - errors)
        if (total - errors) > 0
        else 0.0
    )
    allergen_rates = [
        r["allergen_compliance_rate"] for r in results
        if r.get("allergen_compliance_rate") is not None
    ]
    avg_allergen_rate = sum(allergen_rates) / len(allergen_rates) if allergen_rates else None

    summary = {
        "total_cases": total,
        "passed": passed_count,
        "failed": total - passed_count - errors,
        "errors": errors,
        "pass_rate": round(passed_count / total, 3) if total else 0.0,
        "avg_compliance_rate": round(avg_rate, 3),
        "avg_allergen_compliance_rate": round(avg_allergen_rate, 3) if avg_allergen_rate is not None else None,
        "results": results,
    }

    # Log aggregate score to Langfuse. Note: the SDK pinned in requirements.txt
    # (langfuse>=3.0.0,<4.0.0) replaced the old `.trace()` builder with
    # `start_as_current_span()` + `score_current_trace()` — a call to
    # `langfuse.trace(...)` on this client raises AttributeError and was
    # being silently swallowed by the except below on every eval run.
    try:
        with langfuse.start_as_current_span(
            name="healthcart_eval_run",
            input={"cases_run": total},
            output=summary,
        ) as span:
            trace_id = span.trace_id
            langfuse.score_current_trace(name="eval_pass_rate", value=summary["pass_rate"])
            langfuse.score_current_trace(name="avg_compliance_rate", value=summary["avg_compliance_rate"])
            if avg_allergen_rate is not None:
                langfuse.score_current_trace(
                    name="avg_allergen_compliance_rate", value=avg_allergen_rate
                )
        langfuse.flush()
        print(f"\n  Eval results logged to Langfuse — trace: {trace_id}")
    except Exception as exc:
        print(f"\n  Could not log to Langfuse: {exc}")

    return summary


def print_summary(summary: dict) -> None:
    print("\n" + "=" * 52)
    print("EVAL SUMMARY")
    print("=" * 52)
    print(f"  Cases run        : {summary['total_cases']}")
    print(f"  Passed           : {summary['passed']}")
    print(f"  Failed           : {summary['failed']}")
    print(f"  Errors           : {summary['errors']}")
    print(f"  Pass rate        : {summary['pass_rate']:.0%}")
    print(f"  Avg compliance   : {summary['avg_compliance_rate']:.0%}")
    if summary.get("avg_allergen_compliance_rate") is not None:
        print(f"  Avg allergen     : {summary['avg_allergen_compliance_rate']:.0%}  "
              f"(tracked separately — see ANTHROPIC_EVAL_NOTES.md)")
    print("=" * 52)

    print("\nPer-case breakdown:")
    for r in summary["results"]:
        status = "✓" if r["passed"] else ("!" if r["error"] else "✗")
        allergen_str = (
            f" | allergen {r['allergen_compliance_rate']:.0%}"
            if r.get("allergen_compliance_rate") is not None else ""
        )
        print(
            f"  {status} [{r['test_id']}] {r['name']:<40} "
            f"{r['compliance_rate']:.0%} (min {r['expected_min']:.0%}){allergen_str}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HealthCart eval harness")
    parser.add_argument("--n", type=int, default=None, help="Number of cases to run")
    parser.add_argument("--id", type=str, default=None, help="Run a single case by ID")
    args = parser.parse_args()

    langfuse_client = Langfuse()
    cases = load_cases(n=args.n, case_id=args.id)

    if not cases:
        print(f"No test cases found for id={args.id}")
        exit(1)

    summary = run_eval(cases, langfuse_client)
    print_summary(summary)
