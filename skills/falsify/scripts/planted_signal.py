#!/usr/bin/env python3
"""Gate 4 — planted-signal meta-falsification (falsify skill).

Prove the diagnostic machinery can find a signal that is *obviously* there and
reject obvious noise, BEFORE trusting any WORKING / NOT WORKING verdict.

Two modes (kept deliberately distinct):

  --self-test
      Proves the AUROC computation itself is sound: inject a ~10sigma planted
      signal (positives ~N(1.0, 0.1), negatives ~N(0.0, 0.1)) and confirm AUROC
      is near-perfect; then score pure noise and confirm AUROC sits near 0.5.
      This proves the *ruler*, not the user's pipeline.

  --scores <csv> --score-col <name> --labels-col <name>
      Computes AUROC on the user's own scored output. Proves separation on
      *those* outputs only, not that a strong feature survives their full
      train->infer path.

Pure Python standard library only — runs on any Python 3.8+, no numpy/scipy.

Exit code is 0 only if the requested check passes; non-zero (with a loud
message) otherwise, so it can gate a pipeline.
"""

import argparse
import csv
import random
import sys


# --------------------------------------------------------------------------- #
# Core statistic: AUROC via the Mann-Whitney U identity, tie-aware.
# AUROC = U / (n_pos * n_neg), where U = sum_of_positive_ranks - n_pos*(n_pos+1)/2
# and ranks use average ranks for ties. Validated bit-exact against scipy.
# --------------------------------------------------------------------------- #

def _average_ranks(values):
    """1-based ranks of `values`, ties assigned the average of their positions."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    n = len(order)
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # positions i..j (0-based) -> 1-based average
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def auroc(scores, labels):
    """Area under the ROC curve for binary `labels` (0/1) and real `scores`.

    Raises ValueError on empty input, length mismatch, or a single-class label
    vector (AUROC is undefined) rather than returning a silent NaN.
    """
    if len(scores) != len(labels):
        raise ValueError(
            f"scores and labels length mismatch: {len(scores)} != {len(labels)}"
        )
    if len(scores) == 0:
        raise ValueError("empty input: cannot compute AUROC on zero rows")
    n_pos = sum(1 for v in labels if v == 1)
    n_neg = sum(1 for v in labels if v == 0)
    other = len(labels) - n_pos - n_neg
    if other:
        raise ValueError("labels must be binary 0/1; found other values")
    if n_pos == 0 or n_neg == 0:
        raise ValueError(
            "labels contain only one class; AUROC requires both positives and negatives"
        )
    ranks = _average_ranks(scores)
    sum_pos_ranks = sum(r for r, l in zip(ranks, labels) if l == 1)
    u = sum_pos_ranks - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


# --------------------------------------------------------------------------- #
# Continuous-target metrics (regression / ranking), so the harness is not
# limited to binary classification. Kept local to keep this a single-file
# drop-in. spearman/pearson validated against scipy.
# --------------------------------------------------------------------------- #

def _pearson(x, y):
    import statistics
    import math
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0.0 or dy == 0.0:
        raise ValueError("a column is constant; Pearson r is undefined")
    return num / (dx * dy)


def _spearman(x, y):
    return _pearson(_average_ranks(x), _average_ranks(y))


def compute_metric(metric, scores, targets):
    """Compute the chosen metric between model scores and targets/labels.

    auroc    -> binary classification (targets are 0/1 labels)
    pearson  -> regression / linear (targets are continuous)
    spearman -> ranking / monotonic (targets are continuous or ordinal)
    Raises ValueError on an unknown metric.
    """
    if metric == "auroc":
        return auroc(scores, targets)
    if metric == "pearson":
        return _pearson(scores, targets)
    if metric == "spearman":
        return _spearman(scores, targets)
    raise ValueError(
        f"unknown metric {metric!r}; choose one of ['auroc', 'pearson', 'spearman']")


METRICS = ("auroc", "pearson", "spearman")


# --------------------------------------------------------------------------- #
# Mode A: self-test (prove the ruler)
# --------------------------------------------------------------------------- #

def run_self_test(n=2000, sigma=10.0, seed=0, metric="auroc",
                  floor=None, auroc_floor=None, noise_band=None):
    """Inject a planted signal and pure noise; confirm the metric detects/rejects.

    The shape of the planted signal depends on the metric:
      auroc    -> binary: positives ~N(0.1*sigma, 0.1), negatives ~N(0.0, 0.1);
                  noise = scores independent of labels (AUROC ~ 0.5).
      pearson/ -> regression/ranking: target = score + small noise (strong correlation);
      spearman    noise = target independent of score (correlation ~ 0).

    Floors/bands default per metric: auroc floor 0.99 / band (0.40,0.60);
    pearson & spearman floor 0.8 / band (-0.1, 0.1). Deterministic given `seed`.

    Returns a result dict with unified keys signal_score / noise_score / signal_pass /
    noise_pass, plus legacy signal_auroc / noise_auroc keys when metric == 'auroc'.
    """
    if metric not in METRICS:
        raise ValueError(
            f"unknown metric {metric!r}; choose one of {list(METRICS)}")

    # Back-compat: auroc_floor was the old parameter name; floor is the new generic one.
    if floor is None:
        floor = auroc_floor if auroc_floor is not None else (
            0.99 if metric == "auroc" else 0.8)
    if noise_band is None:
        noise_band = (0.40, 0.60) if metric == "auroc" else (-0.1, 0.1)

    half = n // 2
    rng = random.Random(seed)
    sd = 0.1

    if metric == "auroc":
        mean_sep = sigma * sd
        sig_scores = ([rng.gauss(mean_sep, sd) for _ in range(half)]
                      + [rng.gauss(0.0, sd) for _ in range(half)])
        sig_targets = [1] * half + [0] * half
        noise_scores = [rng.gauss(0.0, 1.0) for _ in range(2 * half)]
        noise_targets = [1] * half + [0] * half
    else:
        # Continuous: target tracks the score (strong linear/monotone signal).
        m = 2 * half
        sig_scores = [rng.gauss(0.0, 1.0) for _ in range(m)]
        sig_targets = [s + rng.gauss(0.0, sd) for s in sig_scores]
        noise_scores = [rng.gauss(0.0, 1.0) for _ in range(m)]
        noise_targets = [rng.gauss(0.0, 1.0) for _ in range(m)]

    signal_score = compute_metric(metric, sig_scores, sig_targets)
    noise_score = compute_metric(metric, noise_scores, noise_targets)

    lo, hi = noise_band
    result = {
        "n": 2 * half,
        "sigma": sigma,
        "seed": seed,
        "metric": metric,
        "floor": floor,
        "noise_band": (lo, hi),
        "signal_score": signal_score,
        "noise_score": noise_score,
        "signal_pass": signal_score >= floor,
        "noise_pass": lo <= noise_score <= hi,
    }
    if metric == "auroc":
        # legacy keys preserved for back-compat with existing tests/CLI.
        result["auroc_floor"] = floor
        result["signal_auroc"] = signal_score
        result["noise_auroc"] = noise_score
    return result


# --------------------------------------------------------------------------- #
# Mode B: score the user's own output
# --------------------------------------------------------------------------- #

def parse_label(value):
    """Parse a binary label string to int 0 or 1; raise ValueError on anything else.

    Rejects fractional ('0.5'), out-of-range ('2', '-1'), and non-finite
    ('inf', 'nan') values rather than silently truncating them — int(float('0.5'))
    would collapse to 0 and corrupt the AUROC silently.
    """
    f = float(value)  # raises ValueError on 'banana'
    if f != f or f in (float("inf"), float("-inf")):  # NaN or inf
        raise ValueError(f"label must be binary 0/1; got non-finite {value!r}")
    if f not in (0.0, 1.0):
        raise ValueError(f"label must be binary 0/1; got {value!r}")
    return int(f)


def _check_unique_headers(fieldnames, path):
    seen, dups = set(), set()
    for c in fieldnames:
        (dups if c in seen else seen).add(c)
    if dups:
        raise ValueError(f"{path}: duplicate column headers: {sorted(dups)}")


def _parse_target(value, metric):
    """Parse a target/label per metric: binary 0/1 for auroc, continuous float otherwise.

    The strict binary check is conditional on metric == 'auroc' — for regression/ranking
    metrics, continuous targets are valid and must NOT be rejected or truncated.
    """
    if metric == "auroc":
        return parse_label(value)
    f = float(value)
    if f != f or f in (float("inf"), float("-inf")):
        raise ValueError(f"target must be finite; got {value!r}")
    return f


def _read_csv_columns(path, score_col, label_col, metric="auroc"):
    scores, targets = [], []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: empty or headerless CSV")
        _check_unique_headers(reader.fieldnames, path)
        for col in (score_col, label_col):
            if col not in reader.fieldnames:
                raise ValueError(
                    f"{path}: column '{col}' not found; have {reader.fieldnames}"
                )
        for row in reader:
            scores.append(float(row[score_col]))
            targets.append(_parse_target(row[label_col], metric))
    return scores, targets


def run_scores_mode(path, score_col, label_col, metric="auroc"):
    scores, targets = _read_csv_columns(path, score_col, label_col, metric)
    return compute_metric(metric, scores, targets)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _parse_band(s):
    """Parse 'lo,hi' into floats. Range/order validation happens after we know the
    metric (AUROC is bounded [0,1]; correlation metrics span [-1,1])."""
    parts = s.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("noise-band must be 'lo,hi'")
    try:
        return (float(parts[0]), float(parts[1]))
    except ValueError:
        raise argparse.ArgumentTypeError("noise-band values must be numbers")


def _positive_int(s):
    v = int(s)
    if v < 4:
        raise argparse.ArgumentTypeError(
            "--n must be >= 4 (need at least 2 positives and 2 negatives)")
    return v


# Valid metric range for floor/band validation: AUROC in [0,1], correlations in [-1,1].
_METRIC_RANGE = {"auroc": (0.0, 1.0), "pearson": (-1.0, 1.0), "spearman": (-1.0, 1.0)}


def build_parser():
    p = argparse.ArgumentParser(
        description="Planted-signal meta-falsification (Gate 4).")
    p.add_argument("--self-test", action="store_true",
                   help="prove the metric finds a planted signal and rejects noise")
    p.add_argument("--scores", help="CSV of the user's own scored output")
    p.add_argument("--score-col", help="name of the score column in --scores")
    p.add_argument("--labels-col",
                   help="name of the label/target column in --scores "
                        "(binary 0/1 for auroc; continuous for pearson/spearman)")
    p.add_argument("--metric", choices=METRICS, default="auroc",
                   help="auroc (binary classification, default), pearson (regression), "
                        "or spearman (ranking/monotonic)")
    p.add_argument("--n", type=_positive_int, default=2000,
                   help="rows for the self-test (default 2000, min 4)")
    p.add_argument("--sigma", type=float, default=10.0,
                   help="standard deviations of separation for the planted signal (auroc)")
    p.add_argument("--seed", type=int, default=0, help="RNG seed (deterministic)")
    p.add_argument("--auroc-floor", dest="floor", type=float, default=None,
                   help="minimum metric value for the signal to count as detected "
                        "(default 0.99 for auroc, 0.8 for correlation metrics)")
    p.add_argument("--noise-band", type=_parse_band, default=None,
                   help="acceptable metric band for noise, 'lo,hi' "
                        "(default '0.40,0.60' for auroc, '-0.1,0.1' for correlations)")
    return p


def _validate_floor_band(metric, floor, noise_band):
    """Validate floor/band against the metric's valid range. Returns an error string or None."""
    lo_r, hi_r = _METRIC_RANGE[metric]
    if floor is not None and not (lo_r <= floor <= hi_r):
        return (f"--auroc-floor must be in [{lo_r},{hi_r}] for metric {metric}; got {floor}")
    if noise_band is not None:
        lo, hi = noise_band
        if not (lo_r <= lo <= hi <= hi_r):
            return (f"--noise-band must satisfy {lo_r} <= lo <= hi <= {hi_r} "
                    f"for metric {metric}; got ({lo},{hi})")
    return None


def main(argv=None):
    args = build_parser().parse_args(argv)

    err = _validate_floor_band(args.metric, args.floor, args.noise_band)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    if args.scores:
        if not args.score_col:
            print("ERROR: --scores requires --score-col (the metric needs a score column "
                  "AND a label/target column).", file=sys.stderr)
            return 2
        if not args.labels_col:
            print("ERROR: --scores requires --labels-col.", file=sys.stderr)
            return 2
        try:
            a = run_scores_mode(args.scores, args.score_col, args.labels_col, args.metric)
        except (ValueError, OSError, OverflowError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(f"{args.metric} on your scored output ({args.scores}): {a:.4f}")
        print("NOTE: this proves the relationship on THESE outputs only — not that a strong "
              "feature survives your full train->infer path. For that, inject a strong "
              "feature upstream and re-run your whole pipeline (Gate 4c).")
        return 0

    # Default to self-test when no --scores given.
    try:
        r = run_self_test(n=args.n, sigma=args.sigma, seed=args.seed, metric=args.metric,
                          floor=args.floor, noise_band=args.noise_band)
    except (ValueError, OverflowError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    metric = r["metric"]
    print(f"[self-test] metric={metric} seed={r['seed']} n={r['n']}")
    sig = "PASS" if r["signal_pass"] else "FAIL"
    noi = "PASS" if r["noise_pass"] else "FAIL"
    print(f"{sig}: stats harness detects the planted signal "
          f"({metric}={r['signal_score']:.4f}, floor={r['floor']})")
    print(f"{noi}: stats harness rejects noise "
          f"({metric}={r['noise_score']:.4f}, band={r['noise_band']})")
    print(f"NOTE: this proves the {metric} math (the ruler), NOT your ML pipeline. "
          "To prove your pipeline, use --scores on its output; the strongest form "
          "injects a strong feature upstream and re-runs the whole pipeline.")
    if r["signal_pass"] and r["noise_pass"]:
        return 0
    print("HARNESS BROKEN: cannot trust any downstream verdict. Fix the plumbing first.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
