"""Command-line entry point.

  python -m expense_pipeline run examples/reports/large_trip.json
  python -m expense_pipeline run examples/reports/blurry_receipt.json --no-validation
  python -m expense_pipeline run examples/reports/large_trip.json --region EU
  python -m expense_pipeline cost
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from expense_pipeline.cost import render_table
from expense_pipeline.orchestrator import Pipeline, load_report
from expense_pipeline.privacy import DataResidencyError


def _run(args: argparse.Namespace) -> int:
    pipeline = Pipeline.default(store_region=args.region)
    report = load_report(Path(args.report))
    print(f"== {report.report_id} ==")
    try:
        result = pipeline.run_report(report, validate=not args.no_validation)
    except DataResidencyError as e:
        print(f"BLOCKED (Step 4 data residency): {e}")
        return 2
    for line in result.transcript:
        print(f"  {line}")
    d = result.decision
    print(f"-> {d.status.value.upper()} | amount={d.amount} | paid={d.paid}")
    print(f"   reason: {d.reason}")
    if args.no_validation and d.paid:
        print("   NOTE: validation was OFF; this is the Step 2 bug (overpayment).")
    return 0


def _cost(_: argparse.Namespace) -> int:
    print(render_table())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="expense_pipeline")
    sub = parser.add_subparsers(required=True)

    p_run = sub.add_parser("run", help="run a report through the pipeline")
    p_run.add_argument("report")
    p_run.add_argument("--no-validation", action="store_true",
                       help="disable Agent 1's validation gate (reproduces the Step 2 bug)")
    p_run.add_argument("--region", default="US", help="data store region (US/EU)")
    p_run.set_defaults(func=_run)

    p_cost = sub.add_parser("cost", help="print the Step 6 cost-driver table")
    p_cost.set_defaults(func=_cost)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
