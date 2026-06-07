#!/usr/bin/env python3
"""Stage 1 — Leakage / split-hygiene check (falsify lifecycle).

Mechanical checks on a CSV that has a train/test split column. Catches the leakage class that
makes a "great model" really train/test contamination:

  HARD failures (exit non-zero):
    - duplicate/identical feature rows spanning train and test
    - temporal overlap: max(train time) >= min(test time)   (needs --time-col)
    - group/entity appearing in both splits                 (needs --group-col)

  SUSPECT (warning, never a hard fail):
    - a single feature that perfectly partitions the label  (needs --label-col)
      Perfect predictors are sometimes legitimate downstream consequences
      (e.g. pregnant -> gave_birth, chargeback-status in a fraud label), so this is
      flagged for human review, not auto-failed.

Pure Python standard library only — runs on any Python 3.8+, no numpy/scipy.
"""

import argparse
import csv
import sys


def _split_value_groups(rows, split_col):
    vals = sorted({r[split_col] for r in rows if r.get(split_col) is not None})
    return vals


def check_duplicate_rows(rows, split_col, feature_cols, min_features=2):
    """Identical feature tuples appearing in more than one split value -> leak.

    Skipped (not a leak) when fewer than `min_features` feature columns are available: a single
    coarse column (e.g. a binary label) "duplicates" trivially and would produce false leaks.
    A real duplicate-leak needs a row's worth of features to match.
    """
    if len(feature_cols) < min_features:
        return {"leak": False, "skipped": True,
                "reason": f"only {len(feature_cols)} feature column(s); need >= {min_features} "
                          f"for a meaningful row-duplicate check (pass --feature-cols)"}
    by_features = {}
    for r in rows:
        key = tuple(r.get(c) for c in feature_cols)
        by_features.setdefault(key, set()).add(r.get(split_col))
    leaking = [k for k, splits in by_features.items() if len(splits) > 1]
    return {"leak": bool(leaking), "skipped": False, "count": len(leaking),
            "examples": [dict(zip(feature_cols, k)) for k in leaking[:5]]}


def check_temporal_overlap(rows, split_col, time_col, test_value=None):
    """A clean temporal split has the TEST set strictly after everything else.

    Leak if any non-test (train) time is >= the test set's minimum time — i.e. the test period
    is not strictly in the future of training. This catches both classic overlap AND the
    "test is in the past" case (test entirely before train), which is equally a leak.

    The test split is identified by `test_value`; if not given, falls back to a split value
    literally named 'test' (case-insensitive), else the lexicographically-last split value.
    Times are parsed as floats.
    """
    splits = _split_value_groups(rows, split_col)
    if len(splits) < 2:
        return {"leak": False, "reason": "fewer than 2 splits; temporal check skipped"}
    times = {s: [] for s in splits}
    for r in rows:
        s = r.get(split_col)
        t = r.get(time_col)
        if s in times and t is not None and str(t).strip() != "":
            times[s].append(float(t))
    present = {s: v for s, v in times.items() if v}
    if len(present) < 2:
        return {"leak": False, "reason": "fewer than 2 splits have times; check skipped"}

    if test_value is not None:
        test = test_value
    else:
        named = [s for s in present if str(s).lower() == "test"]
        test = named[0] if named else sorted(present)[-1]
    if test not in present:
        return {"leak": False, "reason": f"test split '{test}' has no times; check skipped"}

    test_min = min(present[test])
    leak = False
    detail = []
    for s, v in present.items():
        if s == test:
            continue
        if max(v) >= test_min:  # a non-test (train) row at or after the test set's start
            leak = True
            detail.append(f"{s} max={max(v)} >= test '{test}' min={test_min}")
    return {"leak": leak, "test_split": test, "detail": detail}


def check_group_leakage(rows, split_col, group_col):
    """Any group/entity appearing in more than one split value -> leak."""
    by_group = {}
    for r in rows:
        g = r.get(group_col)
        if g is None:
            continue
        by_group.setdefault(g, set()).add(r.get(split_col))
    leaking = sorted(g for g, splits in by_group.items() if len(splits) > 1)
    return {"leak": bool(leaking), "groups": leaking[:10], "count": len(leaking)}


def check_perfect_predictor(rows, label_col, feature_cols):
    """A feature whose value deterministically maps to the label -> SUSPECT (never a fail)."""
    suspects = []
    for c in feature_cols:
        mapping = {}
        ok = True
        for r in rows:
            fv = r.get(c)
            lv = r.get(label_col)
            if fv is None or lv is None:
                continue
            if fv in mapping and mapping[fv] != lv:
                ok = False
                break
            mapping[fv] = lv
        # "perfect" only if the feature actually takes >1 value (constant features are not predictors)
        if ok and len({r.get(c) for r in rows}) > 1 and len(mapping) > 0:
            suspects.append(c)
    return {"suspect": bool(suspects), "features": suspects, "severity": "suspect"}


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
        raise ValueError(f"{path}: duplicate column headers: {sorted(dups)}")
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    return rows, fieldnames


def build_parser():
    p = argparse.ArgumentParser(description="Leakage / split-hygiene check (Stage 1).")
    p.add_argument("--data", help="CSV with a train/test split column")
    p.add_argument("--split-col", help="name of the train/test split column")
    p.add_argument("--time-col", help="time column (enables temporal-overlap check)")
    p.add_argument("--test-value",
                   help="the split value that is the TEST set (default: a value named 'test', "
                        "else the lexicographically-last split value)")
    p.add_argument("--group-col", help="group/entity column (enables group-leakage check)")
    p.add_argument("--label-col", help="label column (enables perfect-predictor suspect check)")
    p.add_argument("--feature-cols",
                   help="comma-separated feature columns for duplicate/perfect-predictor checks; "
                        "default = all columns except split/time/group/label")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.data:
        print("ERROR: --data CSV is required (Stage 1 inspects real data). With no data, answer "
              "templates/data_contract.md by hand.", file=sys.stderr)
        return 2
    if not args.split_col:
        print("ERROR: --split-col is required (names the train/test column).", file=sys.stderr)
        return 2
    try:
        rows, fieldnames = _read_rows(args.data)
        if args.split_col not in fieldnames:
            raise ValueError(f"split column '{args.split_col}' not found; have {fieldnames}")

        reserved = {args.split_col, args.time_col, args.group_col, args.label_col}
        if args.feature_cols:
            feature_cols = [c.strip() for c in args.feature_cols.split(",")]
        else:
            feature_cols = [c for c in fieldnames if c not in reserved]

        hard_leak = False

        dup = check_duplicate_rows(rows, args.split_col, feature_cols)
        if dup["leak"]:
            hard_leak = True
            print(f"LEAK (duplicate rows across split): {dup['count']} identical feature row(s) "
                  f"appear in more than one split. Examples: {dup['examples']}")
        elif dup.get("skipped"):
            print(f"skipped: duplicate-row check ({dup['reason']})")
        else:
            print("ok: no identical feature rows span the split")

        if args.time_col:
            tmp = check_temporal_overlap(rows, args.split_col, args.time_col,
                                         test_value=args.test_value)
            if tmp["leak"]:
                hard_leak = True
                print(f"LEAK (temporal overlap): {tmp['detail']}")
            else:
                print(f"ok: test split is strictly after training in time "
                      f"({tmp.get('reason', 'clean')})")

        if args.group_col:
            grp = check_group_leakage(rows, args.split_col, args.group_col)
            if grp["leak"]:
                hard_leak = True
                print(f"LEAK (group leakage): {grp['count']} group(s) appear in >1 split; "
                      f"e.g. {grp['groups']}")
            else:
                print("ok: no group/entity spans the split")

        if args.label_col:
            pp = check_perfect_predictor(rows, args.label_col, feature_cols)
            if pp["suspect"]:
                print(f"SUSPECT (perfect predictor): feature(s) {pp['features']} perfectly "
                      f"partition the label. This is often leakage, but sometimes a legitimate "
                      f"downstream consequence — HUMAN REVIEW required, not an automatic fail.")
            else:
                print("ok: no single feature perfectly predicts the label")

        if hard_leak:
            print("VERDICT: FAIL — hard leakage found; fix the split before trusting any metric.",
                  file=sys.stderr)
            return 1
        print("VERDICT: PASS — no hard leakage found (review any SUSPECT findings by hand).")
        return 0
    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
