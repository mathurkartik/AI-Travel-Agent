"""
Evaluation harness for GlobeAI travel plans.
Runs golden test cases against the orchestrator and scores structural quality.

Usage:
  python -m backend.eval.evaluate --mock    (fast, no LLM)
  python -m backend.eval.evaluate --live    (real LLM calls)
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

sys.path.insert(0, str(PROJECT_ROOT))


def load_golden_set(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    golden_path = path or (BACKEND_DIR / "eval" / "golden_set.yaml")
    try:
        import yaml
        with open(golden_path, "r") as f:
            data = yaml.safe_load(f)
    except ImportError:
        raise RuntimeError("PyYAML required: pip install pyyaml")
    return data.get("test_cases", [])


def build_mock_response(tc: Dict[str, Any]) -> Dict[str, Any]:
    """Build a static mock plan that matches the golden case structurally."""
    from backend.app.models.schemas import (
        TravelConstraints, FinalItinerary, DayItinerary, DayItineraryItem,
        BudgetBreakdown, BudgetCategory, ReviewStatus, ActivityType,
    )

    days_count = tc["expected_days"]
    destinations = tc.get("expected_destinations", ["Unknown"])
    budget = tc.get("expected_budget_max", 1000)
    currency = tc.get("expected_currency", "USD")

    cities = destinations if len(destinations) > 1 else destinations
    primary = cities[0]

    constraints = TravelConstraints(
        destination_region=primary,
        cities=cities,
        duration_days=days_count,
        budget_total=budget,
        currency=currency,
        preferences=["sightseeing"],
    )

    stub_days: List[DayItinerary] = []
    for day_num in range(1, days_count + 1):
        city = cities[(day_num - 1) % len(cities)]
        items = [
            DayItineraryItem(
                slot_index=0, time="09:00 - 12:00",
                activity_name=f"Morning in {city}",
                city=city, type=ActivityType.OTHER, cost_estimate=20.0,
            ),
            DayItineraryItem(
                slot_index=1, time="14:00 - 18:00",
                activity_name=f"Afternoon in {city}",
                city=city, type=ActivityType.FOOD, cost_estimate=30.0,
            ),
        ]
        stub_days.append(DayItinerary(
            day_number=day_num, city=city, items=items,
            day_summary=f"Day {day_num} in {city}", day_cost=50.0,
        ))

    total_cost = sum(d.day_cost for d in stub_days)

    itinerary = FinalItinerary(
        constraints=constraints,
        days=stub_days,
        neighborhoods={c: [f"Central {c}"] for c in cities},
        logistics_summary=f"Mock plan for {primary}",
        budget_rollup=BudgetBreakdown(
            categories=[
                BudgetCategory(category="stay", estimated_total=round(total_cost * 0.4, 2), currency=currency),
                BudgetCategory(category="food", estimated_total=round(total_cost * 0.3, 2), currency=currency),
                BudgetCategory(category="activities", estimated_total=round(total_cost * 0.2, 2), currency=currency),
                BudgetCategory(category="transport", estimated_total=round(total_cost * 0.1, 2), currency=currency),
            ],
            grand_total=total_cost, currency=currency,
            within_budget=total_cost <= budget, remaining_buffer=budget - total_cost,
        ),
        review_status=ReviewStatus.PASS,
        disclaimer="Mock evaluation plan",
    )
    return {
        "itinerary": itinerary,
        "review_status": "pass",
        "repair_cycles": 0,
    }


async def run_live(tc: Dict[str, Any]) -> Dict[str, Any]:
    """Run a test case through the real orchestrator pipeline."""
    from backend.app.agents.orchestrator import OrchestratorAgent

    orchestrator = OrchestratorAgent()
    start = time.time()
    itinerary = await orchestrator.create_plan(tc["query"], trace_id="eval")
    elapsed = time.time() - start

    return {
        "itinerary": itinerary,
        "review_status": itinerary.review_status,
        "repair_cycles": 0,
        "latency_seconds": round(elapsed, 2),
    }


def check_quality(tc: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    itinerary = result["itinerary"]
    checks = tc.get("quality_checks", [])
    results: Dict[str, bool] = {}
    details: Dict[str, str] = {}

    actual_days = len(itinerary.days)
    expected_days = tc["expected_days"]

    for check in checks:
        if check == "day_count_matches":
            passed = actual_days == expected_days
            results[check] = passed
            if not passed:
                details[check] = f"expected {expected_days}, got {actual_days}"

        elif check == "all_days_have_activities":
            empty = [d.day_number for d in itinerary.days if not d.items]
            results[check] = len(empty) == 0
            if empty:
                details[check] = f"empty days: {empty}"

        elif check == "no_empty_days":
            empty = [d.day_number for d in itinerary.days if not d.items]
            results[check] = len(empty) == 0

        elif check == "budget_within_110_percent":
            budget_max = tc.get("expected_budget_max", float("inf"))
            total = sum(d.day_cost for d in itinerary.days)
            threshold = budget_max * 1.10
            results[check] = total <= threshold
            if not results[check]:
                details[check] = f"total {total} > 110% of {budget_max} ({threshold})"

        elif check == "all_destinations_present":
            expected_dests = set(d.lower() for d in tc.get("expected_destinations", []))
            actual_cities = set(d.city.lower() for d in itinerary.days)
            missing = expected_dests - actual_cities
            results[check] = len(missing) == 0
            if missing:
                details[check] = f"missing: {missing}"

        elif check == "multi_region_structure":
            unique_cities = set(d.city for d in itinerary.days)
            min_dest = tc.get("expected_min_destinations", 3)
            results[check] = len(unique_cities) >= min_dest
            if not results[check]:
                details[check] = f"only {len(unique_cities)} cities, expected >= {min_dest}"

    passed_count = sum(1 for v in results.values() if v)
    total_checks = len(results)

    return {
        "checks": results,
        "details": details,
        "passed": passed_count,
        "total": total_checks,
        "score": round(passed_count / total_checks, 2) if total_checks else 1.0,
    }


async def run_evaluation(mode: str = "mock") -> Dict[str, Any]:
    test_cases = load_golden_set()
    all_results: List[Dict[str, Any]] = []
    total_pass = 0
    total_checks = 0
    total_latency = 0.0
    gate_pass_count = 0
    repair_count = 0

    print(f"\n{'='*60}")
    print(f"  GlobeAI Evaluation Harness — mode: {mode}")
    print(f"  {len(test_cases)} test cases loaded")
    print(f"{'='*60}\n")

    for i, tc in enumerate(test_cases, 1):
        query = tc["query"]
        print(f"[{i}/{len(test_cases)}] {query[:60]}...")

        start = time.time()
        try:
            if mode == "mock":
                result = build_mock_response(tc)
            else:
                result = await run_live(tc)
        except Exception as exc:
            print(f"  FAIL: {exc}")
            all_results.append({
                "query": query,
                "error": str(exc),
                "quality": {"passed": 0, "total": len(tc.get("quality_checks", [])), "score": 0.0},
            })
            continue

        elapsed = time.time() - start
        total_latency += elapsed

        quality = check_quality(tc, result)
        total_pass += quality["passed"]
        total_checks += quality["total"]

        review_status = str(result.get("review_status", "unknown"))
        if review_status == "pass":
            gate_pass_count += 1
        repair_count += result.get("repair_cycles", 0)

        status = "PASS" if quality["score"] == 1.0 else "PARTIAL" if quality["score"] > 0 else "FAIL"
        print(f"  {status} ({quality['passed']}/{quality['total']} checks) [{elapsed:.1f}s]")

        for check_name, passed in quality["checks"].items():
            if not passed:
                detail = quality["details"].get(check_name, "")
                print(f"    FAIL: {check_name} — {detail}")

        all_results.append({
            "query": query,
            "quality": quality,
            "review_status": review_status,
            "repair_cycles": result.get("repair_cycles", 0),
            "latency_seconds": round(elapsed, 2),
        })

    overall_score = round(total_pass / total_checks, 3) if total_checks else 0.0
    n = len(test_cases)

    summary = {
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": n,
        "structural_completeness": overall_score,
        "quality_gate_pass_rate": round(gate_pass_count / n, 2) if n else 0.0,
        "repair_rate": round(repair_count / n, 2) if n else 0.0,
        "total_repairs": repair_count,
        "avg_latency_seconds": round(total_latency / n, 2) if n else 0.0,
        "results": all_results,
    }

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"  Structural completeness: {overall_score:.1%}")
    print(f"  Quality gate pass rate:  {summary['quality_gate_pass_rate']:.0%}")
    print(f"  Repair rate:             {summary['repair_rate']:.2f} repairs/plan")
    print(f"  Avg latency:             {summary['avg_latency_seconds']:.2f}s")
    print(f"{'='*60}\n")

    report_path = BACKEND_DIR / "eval" / "eval_report.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Report saved to {report_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="GlobeAI Evaluation Harness")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--mock", action="store_true", help="Use static mock data (fast, no LLM)")
    group.add_argument("--live", action="store_true", help="Use real LLM calls (slow, costs tokens)")
    args = parser.parse_args()

    mode = "live" if args.live else "mock"
    asyncio.run(run_evaluation(mode))


if __name__ == "__main__":
    main()
