#!/usr/bin/env python3
"""Gate 5 — closed-loop mutual-exclusivity diagnostic (falsify skill).

Catches the most expensive failure: a model that scores beautifully in-sample
while measuring nothing real. It correlates the model's in-sample score against
an INDEPENDENT oracle score on the same cases, and (optionally) checks whether
the variants that fit best in-sample are the ones with the lowest oracle
correlation — the direct signature of a closed loop.

Inputs are two CSVs joined on a shared id column (never by row order, because
independent oracle data rarely arrives in the same order). Reports Spearman rho
with a 95% percentile bootstrap CI.

Pure Python standard library only — runs on any Python 3.8+, no numpy/scipy.
"""

import argparse
import csv
import math
import random
import statistics
import sys


# --------------------------------------------------------------------------- #
# Spearman rho: Pearson correlation on average ranks. Tie-aware. Validated
# bit-exact against scipy.stats.spearmanr.
# --------------------------------------------------------------------------- #

def _average_ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    n = len(order)
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(x, y):
    """Spearman rank correlation between x and y.

    Raises ValueError on length mismatch, fewer than 2 points, or a constant
    column (rho undefined) rather than returning a silent NaN.
    """
    if len(x) != len(y):
        raise ValueError(f"length mismatch: {len(x)} != {len(y)}")
    if len(x) < 2:
        raise ValueError("need at least 2 paired points for a correlation")
    rx = _average_ranks(x)
    ry = _average_ranks(y)
    mx = statistics.fmean(rx)
    my = statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if dx == 0.0 or dy == 0.0:
        raise ValueError("a column is constant; Spearman rho is undefined")
    return num / (dx * dy)


def pearson(x, y):
    """Pearson linear correlation between x and y.

    For regression-style claims where the relationship is expected to be linear/continuous.
    Raises ValueError on length mismatch, fewer than 2 points, or a constant column
    (r undefined) rather than returning a silent NaN. Validated against scipy.stats.pearsonr.
    """
    if len(x) != len(y):
        raise ValueError(f"length mismatch: {len(x)} != {len(y)}")
    if len(x) < 2:
        raise ValueError("need at least 2 paired points for a correlation")
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0.0 or dy == 0.0:
        raise ValueError("a column is constant; Pearson r is undefined")
    return num / (dx * dy)


# Metric registry: task -> correlation function.
#   spearman  -> ranking / monotonic relationships (default; tie-aware ranks)
#   pearson   -> regression / linear relationships
_CORRELATIONS = {"spearman": spearman, "pearson": pearson}


def correlation(metric, x, y):
    """Dispatch to the named correlation. Raises ValueError on an unknown metric."""
    fn = _CORRELATIONS.get(metric)
    if fn is None:
        raise ValueError(
            f"unknown metric {metric!r}; choose one of {sorted(_CORRELATIONS)}")
    return fn(x, y)


def bootstrap_ci(x, y, n_bootstrap=2000, seed=0, alpha=0.05, metric="spearman"):
    """95% percentile bootstrap CI for the chosen correlation (resample paired rows)."""
    rng = random.Random(seed)
    m = len(x)
    vals = []
    for _ in range(n_bootstrap):
        idx = [rng.randrange(m) for _ in range(m)]
        bx = [x[i] for i in idx]
        by = [y[i] for i in idx]
        try:
            vals.append(correlation(metric, bx, by))
        except ValueError:
            # A resample can be all-ties / constant column; skip it.
            continue
    if not vals:
        raise ValueError("bootstrap produced no valid resamples (degenerate data)")
    vals.sort()
    lo_i = int((alpha / 2.0) * len(vals))
    hi_i = min(len(vals) - 1, int((1.0 - alpha / 2.0) * len(vals)))
    return vals[lo_i], vals[hi_i]


# --------------------------------------------------------------------------- #
# Pairing: join two id-keyed row lists. Never positional unless asked.
# --------------------------------------------------------------------------- #

def _index_by_id(rows, id_col, val_col, which):
    out = {}
    for r in rows:
        if id_col not in r:
            raise ValueError(f"{which}: id column '{id_col}' not found; have {list(r)}")
        if val_col not in r:
            raise ValueError(f"{which}: value column '{val_col}' not found; have {list(r)}")
        rid = r[id_col]
        if rid in out:
            raise ValueError(f"{which}: duplicate id '{rid}' makes the join ambiguous")
        out[rid] = float(r[val_col])
    return out


def join_on_id(in_rows, in_id_col, in_val_col, oracle_rows, oracle_id_col, oracle_val_col):
    """Join in-sample and oracle rows on id; return (xs, ys) in in-file order.

    Raises ValueError on duplicate ids or any id present in one file but not the
    other (unmatched ids are a loud error, not a silent drop).
    """
    in_idx = _index_by_id(in_rows, in_id_col, in_val_col, "in-sample")
    or_idx = _index_by_id(oracle_rows, oracle_id_col, oracle_val_col, "oracle")
    in_ids = set(in_idx)
    or_ids = set(or_idx)
    missing_in_oracle = in_ids - or_ids
    missing_in_insample = or_ids - in_ids
    if missing_in_oracle or missing_in_insample:
        def _fmt(missing):
            shown = sorted(missing, key=str)[:10]
            extra = len(missing) - len(shown)
            tail = f" (and {extra} more; {len(missing)} total)" if extra else ""
            return f"{shown}{tail}"
        parts = []
        if missing_in_oracle:
            parts.append(f"in-sample ids absent from oracle: {_fmt(missing_in_oracle)}")
        if missing_in_insample:
            parts.append(f"oracle ids absent from in-sample: {_fmt(missing_in_insample)}")
        raise ValueError("unmatched ids — " + "; ".join(parts))
    xs, ys = [], []
    for r in in_rows:  # preserve in-file order, deterministic
        rid = r[in_id_col]
        xs.append(in_idx[rid])
        ys.append(or_idx[rid])
    return xs, ys


def pair_by_position(in_rows, in_val_col, oracle_rows, oracle_val_col):
    """Positional pairing (only when the caller asserts both files are aligned)."""
    if len(in_rows) != len(oracle_rows):
        raise ValueError(
            f"--assume-aligned but row counts differ: {len(in_rows)} != {len(oracle_rows)}")
    xs = [float(r[in_val_col]) for r in in_rows]
    ys = [float(r[oracle_val_col]) for r in oracle_rows]
    return xs, ys


# --------------------------------------------------------------------------- #
# Power status and variant signature.
# --------------------------------------------------------------------------- #

def power_status(n, min_n=20, warn_n=30):
    """Reject below min_n; flag underpowered below warn_n (review #5)."""
    return {
        "n": n,
        "min_n": min_n,
        "warn_n": warn_n,
        "reject": n < min_n,
        "underpowered": (min_n <= n < warn_n),
    }


def variant_signature(in_sample_fits, oracle_corrs):
    """Closed-loop signature: best in-sample variants have lowest oracle corr.

    Returns the rank correlation between the two columns; negative means the
    architecture is learning the generator, not the signal (PROTOCOL move #3).
    """
    rho = spearman(in_sample_fits, oracle_corrs)
    return {"variant_rho": rho, "closed_loop_signature": rho < 0.0}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _read_rows(path):
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
        # DictReader silently keeps the last of duplicate headers, which would
        # corrupt the join or the score column. Refuse loudly instead.
        raise ValueError(f"{path}: duplicate column headers: {sorted(dups)}")
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    return rows


def _require_columns(rows, cols, which):
    have = list(rows[0]) if rows else []
    for c in cols:
        if c not in have:
            raise ValueError(f"{which}: column '{c}' not found; have {have}")


def _positive_int(s):
    v = int(s)
    if v < 1:
        raise argparse.ArgumentTypeError("must be a positive integer (>= 1)")
    return v


def build_parser():
    p = argparse.ArgumentParser(
        description="Closed-loop mutual-exclusivity diagnostic (Gate 5).")
    p.add_argument("--in-sample", required=True, help="CSV of in-sample scores")
    p.add_argument("--in-col", required=True, help="in-sample score column name")
    p.add_argument("--oracle", required=True, help="CSV of independent oracle scores")
    p.add_argument("--oracle-col", required=True, help="oracle score column name")
    p.add_argument("--id-col", help="shared id column (same name in both files)")
    p.add_argument("--in-id-col", help="id column in the in-sample file")
    p.add_argument("--oracle-id-col", help="id column in the oracle file")
    p.add_argument("--assume-aligned", action="store_true",
                   help="pair by row order instead of id (asserts both files aligned)")
    p.add_argument("--variants", help="CSV with columns in_sample_fit,oracle_corr per variant")
    p.add_argument("--n-bootstrap", type=_positive_int, default=2000,
                   help="bootstrap resamples (default 2000, min 1)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--min-n", type=_positive_int, default=20,
                   help="reject below this n (default 20)")
    p.add_argument("--warn-n", type=int, default=30, help="flag UNDERPOWERED below this n")
    p.add_argument("--metric", choices=sorted(_CORRELATIONS), default="spearman",
                   help="correlation metric: spearman (ranking/monotonic, default) "
                        "or pearson (regression/linear)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        in_rows = _read_rows(args.in_sample)
        oracle_rows = _read_rows(args.oracle)

        if args.assume_aligned:
            print("WARNING: --assume-aligned pairs by row order; assumes both files "
                  "are in identical order.", file=sys.stderr)
            xs, ys = pair_by_position(in_rows, args.in_col, oracle_rows, args.oracle_col)
        else:
            in_id = args.in_id_col or args.id_col
            or_id = args.oracle_id_col or args.id_col
            if not in_id or not or_id:
                print("ERROR: provide --id-col (or --in-id-col/--oracle-id-col), or "
                      "--assume-aligned if both files are already row-aligned.",
                      file=sys.stderr)
                return 2
            xs, ys = join_on_id(in_rows, in_id, args.in_col,
                                oracle_rows, or_id, args.oracle_col)

        n = len(xs)
        ps = power_status(n, min_n=args.min_n, warn_n=args.warn_n)
        if ps["reject"]:
            print(f"ERROR: n={n} is below --min-n={args.min_n}; sample too small for a "
                  f"credible external claim (PROTOCOL gap #8).", file=sys.stderr)
            return 2

        rho = correlation(args.metric, xs, ys)
        lo, hi = bootstrap_ci(xs, ys, n_bootstrap=args.n_bootstrap, seed=args.seed,
                              metric=args.metric)
        label = {"spearman": "Spearman rho", "pearson": "Pearson r"}[args.metric]
        print(f"oracle correlation ({args.metric}): {label}={rho:.4f}  "
              f"95% CI=[{lo:.4f}, {hi:.4f}]  n={n}")

        if ps["underpowered"]:
            print(f"UNDERPOWERED: n={n} is below warn-n={args.warn_n}; treat the CI with "
                  f"caution and downgrade confidence.")

        if lo <= 0.0:
            print("CLOSED-LOOP RISK: external correlation not distinguishable from zero "
                  "(CI lower bound <= 0). The in-sample number may be measuring your own "
                  "generator, not reality. Lean toward NOT WORKING.")
        else:
            print("External support present: oracle correlation CI clears zero.")

        if args.variants:
            vrows = _read_rows(args.variants)
            _require_columns(vrows, ("in_sample_fit", "oracle_corr"), args.variants)
            fits = [float(r["in_sample_fit"]) for r in vrows]
            ocs = [float(r["oracle_corr"]) for r in vrows]
            sig = variant_signature(fits, ocs)
            print(f"variant in-sample-vs-oracle rho = {sig['variant_rho']:.4f}")
            if sig["closed_loop_signature"]:
                print("CLOSED-LOOP SIGNATURE: best in-sample variants have lowest oracle "
                      "correlation. The architecture is learning the generator, not the "
                      "signal. Strongest evidence of a closed loop.")
        return 0

    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
