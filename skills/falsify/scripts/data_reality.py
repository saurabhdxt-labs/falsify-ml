#!/usr/bin/env python3
"""Stage 1.5 — Data Reality / feasibility check (falsify lifecycle).

Answers the question Stage 1 (leakage) does NOT: even with perfectly clean data, can the data
PHYSICALLY support the claim? Two modes:

  numbers mode (idea stage, no data yet):
    --n --target-effect [--alpha --power]    -> minimum detectable correlation + a verdict
    --label-error-rate --required-precision  -> achievable precision ceiling + a verdict

  CSV mode (data exists):
    --data file.csv --label-col y [--gold-col y_gold]
      -> n, label base rate, per-column missingness, and (if a re-labeled gold column is given)
         the label-disagreement rate as a noise proxy.

Pure Python standard library only — runs on any Python 3.8+, no numpy/scipy. The power math uses
Acklam's inverse-normal approximation + the Fisher-z transform, validated bit-accurate vs scipy.
"""

import argparse
import csv
import math
import sys


# --------------------------------------------------------------------------- #
# Inverse normal CDF (Acklam's approximation; abs error < 1.15e-9). stdlib only.
# --------------------------------------------------------------------------- #

def norm_ppf(p):
    """Quantile of the standard normal. Raises ValueError outside (0,1)."""
    if not (0.0 < p < 1.0):
        raise ValueError(f"norm_ppf requires 0 < p < 1; got {p}")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p <= 1 - plow:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
           ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)


# --------------------------------------------------------------------------- #
# Feasibility kernels.
# --------------------------------------------------------------------------- #

def min_detectable_r(n, alpha=0.05, power=0.8):
    """Smallest correlation a two-sided test at `alpha` detects with `power` at sample size n.

    Fisher-z: se = 1/sqrt(n-3); required z-effect = z_{1-alpha/2} + z_{power}. Raises on n<4.
    Validated against scipy: n=20 -> 0.59118, n=100 -> 0.27703, n=300 -> 0.16115.
    """
    if n < 4:
        raise ValueError("need n >= 4 for a correlation power estimate")
    z = (norm_ppf(1 - alpha / 2.0) + norm_ppf(power)) / math.sqrt(n - 3)
    return math.tanh(z)


def precision_ceiling(label_error_rate):
    """Max achievable precision/accuracy against observed labels given a label-error fraction.

    A perfect predictor of the TRUE label agrees with the observed label on the (1-e) correct
    rows, so the ceiling is 1 - e. Raises outside [0,1].
    """
    if not (0.0 <= label_error_rate <= 1.0):
        raise ValueError(f"label_error_rate must be in [0,1]; got {label_error_rate}")
    return 1.0 - label_error_rate


def power_verdict(n, target_effect, alpha=0.05, power=0.8):
    """Is the target effect detectable at this n? Returns a dict with the min-detectable r."""
    mdr = min_detectable_r(n, alpha=alpha, power=power)
    return {"n": n, "target_effect": abs(target_effect), "min_detectable_r": mdr,
            "detectable": abs(target_effect) >= mdr}


def precision_verdict(label_error_rate, required_precision):
    """Is the required precision achievable given the label-noise ceiling?"""
    ceil = precision_ceiling(label_error_rate)
    return {"label_error_rate": label_error_rate, "required_precision": required_precision,
            "ceiling": ceil, "achievable": required_precision <= ceil}


# --------------------------------------------------------------------------- #
# CSV inspection.
# --------------------------------------------------------------------------- #

def _is_missing(v):
    return v is None or str(v).strip() == ""


def inspect_csv(path, label_col, gold_col=None):
    """Report n, label base rate, per-column missingness, and (optional) gold disagreement."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if fieldnames is None:
        raise ValueError(f"{path}: empty or headerless CSV")
    seen, dups = set(), set()
    for c in fieldnames:
        (dups if c in seen else seen).add(c)
    if dups:
        raise ValueError(f"{path}: duplicate column headers: {sorted(dups)}")
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    if label_col not in fieldnames:
        raise ValueError(f"{path}: label column '{label_col}' not found; have {fieldnames}")

    n = len(rows)
    missingness = {}
    for col in fieldnames:
        missingness[col] = sum(1 for r in rows if _is_missing(r.get(col))) / n

    labels = [r[label_col] for r in rows if not _is_missing(r.get(label_col))]
    base_rate = None
    try:
        nums = [float(v) for v in labels]
        if nums and all(v in (0.0, 1.0) for v in nums):
            base_rate = sum(nums) / len(nums)
    except ValueError:
        base_rate = None  # non-numeric labels; base rate not defined

    report = {"n": n, "base_rate": base_rate, "missingness": missingness}

    if gold_col is not None:
        if gold_col not in fieldnames:
            raise ValueError(f"{path}: gold column '{gold_col}' not found; have {fieldnames}")
        pairs = [(r[label_col], r[gold_col]) for r in rows
                 if not _is_missing(r.get(label_col)) and not _is_missing(r.get(gold_col))]
        if not pairs:
            raise ValueError("no rows with both label and gold present")
        dis = sum(1 for a, b in pairs if a != b) / len(pairs)
        report["gold_disagreement"] = dis
        report["gold_n"] = len(pairs)
    return report


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser():
    p = argparse.ArgumentParser(description="Data reality / feasibility check (Stage 1.5).")
    # CSV mode
    p.add_argument("--data", help="CSV to inspect (n, balance, missingness, gold disagreement)")
    p.add_argument("--label-col", help="label column in --data")
    p.add_argument("--gold-col", help="re-labeled gold column (label-noise proxy)")
    # numbers mode: power
    p.add_argument("--n", type=int, help="sample size (numbers mode)")
    p.add_argument("--target-effect", type=float,
                   help="correlation you need to detect (numbers mode)")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.8)
    # numbers mode: precision ceiling
    p.add_argument("--label-error-rate", type=float, help="estimated label error fraction [0,1]")
    p.add_argument("--required-precision", type=float, help="precision the use-case requires")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    did_something = False
    try:
        if args.data:
            if not args.label_col:
                print("ERROR: --data requires --label-col.", file=sys.stderr)
                return 2
            rep = inspect_csv(args.data, args.label_col, args.gold_col)
            print(f"[data reality] n={rep['n']}")
            if rep["base_rate"] is not None:
                print(f"  label base rate: {rep['base_rate']:.4f}")
            worst = sorted(rep["missingness"].items(), key=lambda kv: -kv[1])[:5]
            print("  missingness (top cols): " +
                  ", ".join(f"{c}={m:.2f}" for c, m in worst))
            if "gold_disagreement" in rep:
                d = rep["gold_disagreement"]
                print(f"  gold disagreement (label-noise proxy): {d:.4f} on {rep['gold_n']} rows")
                print(f"  -> implied precision ceiling: {precision_ceiling(d):.4f}")
            did_something = True

        if args.n is not None and args.target_effect is not None:
            v = power_verdict(args.n, args.target_effect, alpha=args.alpha, power=args.power)
            verdict = "PASS (detectable)" if v["detectable"] else "FAIL (NOT reliably detectable)"
            print(f"[power] n={v['n']} detects correlations >= {v['min_detectable_r']:.4f} "
                  f"(alpha={args.alpha}, power={args.power}); "
                  f"your target {v['target_effect']:.4f} -> {verdict}")
            if not v["detectable"]:
                print("  -> NEEDS-MORE data, or the effect is too weak to detect at this n.")
            did_something = True

        if args.label_error_rate is not None and args.required_precision is not None:
            v = precision_verdict(args.label_error_rate, args.required_precision)
            if v["achievable"]:
                print(f"[precision] ceiling {v['ceiling']:.4f} >= required "
                      f"{v['required_precision']:.4f} -> PASS (achievable)")
            else:
                print(f"[precision] ceiling {v['ceiling']:.4f} < required "
                      f"{v['required_precision']:.4f} -> DO NOT PURSUE: required precision is "
                      f"above the label-noise ceiling (not achievable).")
            did_something = True

        if not did_something:
            print("ERROR: provide --data (+ --label-col) for CSV mode, OR --n + --target-effect, "
                  "OR --label-error-rate + --required-precision for numbers mode.",
                  file=sys.stderr)
            return 2
        return 0
    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
