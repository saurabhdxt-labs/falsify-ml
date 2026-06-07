#!/usr/bin/env python3
"""Stage 2.5 — Value / Economics check (falsify lifecycle).

A project can be scientifically sound (signal present, data clean, metric valid) and still be a
bad project because the economics don't work — the classic "1% lift, $2M to deploy" case. This
does the part of the value question that is mechanical arithmetic; the judgment inputs (what is a
unit of improvement worth? what does deployment cost?) come from templates/value_case.md.

Model (one period, e.g. one year):
  gross_gain   = value_per_unit * expected_lift
  annual_net   = gross_gain - annual_maintenance
  net_year1    = gross_gain - deploy_cost - annual_maintenance
  payback_years = deploy_cost / annual_net   (only if annual_net > 0; else the deploy never recovers)

Verdict:
  PASS  — annual_net > 0 AND deploy recovers (finite payback)
  FAIL  — annual_net <= 0 (gains don't even cover ongoing cost; deploy never recovers)

Pure Python standard library only — runs on any Python 3.8+, no deps.
"""

import argparse
import sys


def compute_value(value_per_unit, expected_lift, deploy_cost, annual_maintenance):
    """Compute the value case and a PASS/FAIL verdict. Raises on negative inputs."""
    for name, v in (("value_per_unit", value_per_unit), ("expected_lift", expected_lift),
                    ("deploy_cost", deploy_cost), ("annual_maintenance", annual_maintenance)):
        if v < 0:
            raise ValueError(f"{name} must be >= 0; got {v}")
    gross_gain = value_per_unit * expected_lift
    annual_net = gross_gain - annual_maintenance
    net_year1 = gross_gain - deploy_cost - annual_maintenance
    if annual_net > 0:
        payback_years = deploy_cost / annual_net
        verdict = "PASS"
    else:
        payback_years = None  # deploy cost never recovers
        verdict = "FAIL"
    return {
        "gross_gain": gross_gain,
        "annual_net": annual_net,
        "net_year1": net_year1,
        "payback_years": payback_years,
        "verdict": verdict,
    }


def build_parser():
    p = argparse.ArgumentParser(description="Value / economics check (Stage 2.5).")
    p.add_argument("--value-per-unit", type=float, help="value of one unit of improvement")
    p.add_argument("--expected-lift", type=float, help="units of improvement the model is expected to add")
    p.add_argument("--deploy-cost", type=float, help="one-time cost to build & deploy")
    p.add_argument("--annual-maintenance", type=float, help="ongoing cost per period")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    missing = [n for n, v in (("--value-per-unit", args.value_per_unit),
                              ("--expected-lift", args.expected_lift),
                              ("--deploy-cost", args.deploy_cost),
                              ("--annual-maintenance", args.annual_maintenance)) if v is None]
    if missing:
        print(f"UNKNOWN: value case needs {', '.join(missing)}. Fill templates/value_case.md and "
              f"pass all four numbers. Stage 2.5 status = UNKNOWN until then.", file=sys.stderr)
        return 2
    try:
        r = compute_value(args.value_per_unit, args.expected_lift,
                          args.deploy_cost, args.annual_maintenance)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"[value] gross gain/period = {r['gross_gain']:.2f}; "
          f"annual net (after maintenance) = {r['annual_net']:.2f}; "
          f"year-1 net (after deploy) = {r['net_year1']:.2f}")
    if r["verdict"] == "PASS":
        print(f"PASS: deploy cost recovers in {r['payback_years']:.2f} period(s); "
              f"economics support pursuing.")
    else:
        print("DO NOT PURSUE (economics): annual gains do not cover ongoing cost — the deploy "
              "investment never recovers, regardless of model quality. (Stage 2.5 = FAIL.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
