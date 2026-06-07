"""Tests for closed_loop_check.py (Gate 5 — closed-loop mutual-exclusivity).

Spearman values are grounded against a scipy oracle (computed once, hard-coded):
  - x=[1,2,3,4,5] vs y=[1,2,3,5,4]  -> rho = 0.9
  - perfect positive               -> 1.0
  - perfect anti-correlation       -> -1.0

Manual-mutation rehearsal (CLAUDE.md Part 1 rule 22):
  - replacing average-rank ties with positional ranks breaks test_spearman_with_ties;
  - dropping the n<min_n guard breaks test_min_n_rejects;
  - pairing by row order instead of id breaks test_id_join_reorders.
"""

import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "falsify" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import closed_loop_check as clc  # noqa: E402

_SCRIPT = _SCRIPTS_DIR / "closed_loop_check.py"
_TOL = 1e-9


# ------------------------------ spearman() correctness ------------------------------

def test_spearman_known_value():
    """spearman == 0.9 on the oracle fixture. Red if the rank-correlation math is wrong."""
    assert abs(clc.spearman([1, 2, 3, 4, 5], [1, 2, 3, 5, 4]) - 0.9) < _TOL


def test_spearman_perfect_positive():
    assert abs(clc.spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < _TOL


def test_spearman_perfect_anti():
    """Perfect anti-correlation -> -1.0. This is the closed-loop signature direction."""
    assert abs(clc.spearman([1, 2, 3, 4], [4, 3, 2, 1]) - (-1.0)) < _TOL


def test_spearman_with_ties():
    """Tie-aware ranks. Red if ties use positional instead of average ranks."""
    # x has a tie; compare against scipy-derived value 0.9746794344808963
    val = clc.spearman([1, 2, 2, 3, 4], [1, 2, 3, 4, 5])
    assert abs(val - 0.9746794344808963) < 1e-9


def test_spearman_constant_column_raises():
    """A constant column makes rho undefined -> loud error, not silent NaN."""
    try:
        clc.spearman([1, 1, 1, 1], [1, 2, 3, 4])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for constant column")


# ------------------------------ pearson() correctness ------------------------------

def test_pearson_known_value():
    """pearson == 0.7745966692414834 on the oracle fixture (scipy-derived). Red if math wrong."""
    val = clc.pearson([1, 2, 3, 4, 5], [2, 4, 5, 4, 5])
    assert abs(val - 0.7745966692414834) < 1e-12


def test_pearson_perfect_linear():
    """Perfectly linear data -> 1.0 (Pearson is invariant to positive affine scaling)."""
    assert abs(clc.pearson([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < _TOL


def test_pearson_perfect_anti():
    assert abs(clc.pearson([1, 2, 3, 4], [4, 3, 2, 1]) - (-1.0)) < _TOL


def test_pearson_constant_column_raises():
    """Constant column -> r undefined -> loud error, not silent NaN."""
    try:
        clc.pearson([2, 2, 2, 2], [1, 2, 3, 4])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for constant column")


def test_correlation_dispatch():
    """clc.correlation(metric, x, y) dispatches to spearman/pearson and rejects unknown."""
    assert abs(clc.correlation("spearman", [1, 2, 3], [1, 2, 3]) - 1.0) < _TOL
    assert abs(clc.correlation("pearson", [1, 2, 3], [2, 4, 6]) - 1.0) < _TOL
    try:
        clc.correlation("nonsense", [1, 2, 3], [1, 2, 3])
    except ValueError:
        pass
    else:
        raise AssertionError("unknown metric must raise")


# ------------------------------ bootstrap CI ------------------------------

def test_bootstrap_ci_brackets_point_estimate():
    """The 95% percentile CI brackets the point estimate for a strong correlation."""
    x = list(range(40))
    y = [v + (1 if v % 7 == 0 else 0) for v in x]  # near-perfect monotone
    rho = clc.spearman(x, y)
    lo, hi = clc.bootstrap_ci(x, y, n_bootstrap=500, seed=42)
    assert lo <= rho <= hi
    assert lo > 0.0  # strong positive: CI lower bound clears zero


def test_bootstrap_ci_deterministic():
    """Same seed -> same CI (reproducibility, CLAUDE.md Part 1 rule 19)."""
    x = list(range(30)); y = [v * 2 for v in x]
    a = clc.bootstrap_ci(x, y, n_bootstrap=200, seed=7)
    b = clc.bootstrap_ci(x, y, n_bootstrap=200, seed=7)
    assert a == b


# ------------------------------ id-join pairing ------------------------------

def test_id_join_reorders():
    """join_on_id pairs by id even when the two files are in different row orders."""
    in_rows = [{"id": "a", "s": "1"}, {"id": "b", "s": "2"}, {"id": "c", "s": "3"}]
    or_rows = [{"id": "c", "o": "30"}, {"id": "a", "o": "10"}, {"id": "b", "o": "20"}]
    xs, ys = clc.join_on_id(in_rows, "id", "s", or_rows, "id", "o")
    # paired in in-file order: a->10, b->20, c->30
    assert xs == [1.0, 2.0, 3.0]
    assert ys == [10.0, 20.0, 30.0]


def test_id_join_unmatched_raises():
    """An id present in one file but not the other is a loud error."""
    in_rows = [{"id": "a", "s": "1"}, {"id": "b", "s": "2"}]
    or_rows = [{"id": "a", "o": "10"}]  # missing b
    try:
        clc.join_on_id(in_rows, "id", "s", or_rows, "id", "o")
    except ValueError as e:
        assert "b" in str(e)
    else:
        raise AssertionError("expected ValueError for unmatched id")


def test_id_join_duplicate_raises():
    """A duplicate id makes the join ambiguous -> loud error."""
    in_rows = [{"id": "a", "s": "1"}, {"id": "a", "s": "2"}]
    or_rows = [{"id": "a", "o": "10"}]
    try:
        clc.join_on_id(in_rows, "id", "s", or_rows, "id", "o")
    except ValueError as e:
        assert "duplicate" in str(e).lower()
    else:
        raise AssertionError("expected ValueError for duplicate id")


# ------------------------------ underpowered guard ------------------------------

def test_min_n_rejects():
    """n below --min-n is rejected loudly (review #5: n=8 is underpowered)."""
    assert clc.power_status(n=10, min_n=20)["reject"] is True


def test_underpowered_warning_band():
    """20 <= n < 30 is accepted but flagged UNDERPOWERED."""
    st = clc.power_status(n=25, min_n=20)
    assert st["reject"] is False
    assert st["underpowered"] is True


def test_well_powered():
    st = clc.power_status(n=50, min_n=20)
    assert st["reject"] is False and st["underpowered"] is False


# ------------------------------ variant anti-correlation signature ------------------------------

def test_variant_signature_fires_on_anticorrelation():
    """Best-in-sample variants having lowest oracle corr -> signature fires (move #3)."""
    fits = [0.95, 0.80, 0.60, 0.40]      # in-sample fit, descending
    oracles = [0.05, 0.20, 0.45, 0.70]   # oracle corr, ascending -> anti-correlated
    assert clc.variant_signature(fits, oracles)["closed_loop_signature"] is True


def test_variant_signature_quiet_when_aligned():
    fits = [0.9, 0.7, 0.5]
    oracles = [0.8, 0.6, 0.4]  # aligned -> no signature
    assert clc.variant_signature(fits, oracles)["closed_loop_signature"] is False


# ------------------------------ CLI end-to-end ------------------------------

def _run_cli(*args):
    return subprocess.run([sys.executable, str(_SCRIPT), *args],
                          capture_output=True, text=True)


def test_cli_reports_rho_ci_n(tmp_path):
    """CLI prints NUMERIC rho/CI/n that match the data — not just the keyword strings.

    Strengthened after the adversarial review: the old version asserted only that the
    substrings 'rho'/'ci'/'n=' appeared, so a CLI printing 'rho=NaN ci=error n=wrong'
    survived. This parses the actual numbers and checks them against the fixture.
    """
    import re
    insamp = tmp_path / "in.csv"; oracle = tmp_path / "or.csv"
    ids = list(range(40))
    insamp.write_text("id,s\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    oracle.write_text("id,o\n" + "\n".join(f"{i},{i+ (1 if i%5==0 else 0)}" for i in ids) + "\n")
    proc = _run_cli("--in-sample", str(insamp), "--in-col", "s",
                    "--oracle", str(oracle), "--oracle-col", "o", "--id-col", "id")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout + proc.stderr
    m = re.search(r"rho=([-\d.]+)\s+95% CI=\[([-\d.]+),\s*([-\d.]+)\]\s+n=(\d+)", out)
    assert m, f"could not parse numeric rho/CI/n from output:\n{out}"
    rho, lo, hi, n = float(m[1]), float(m[2]), float(m[3]), int(m[4])
    assert n == 40
    assert -1.0 <= rho <= 1.0 and rho > 0.9  # near-monotone data -> strong positive
    assert lo <= rho <= hi  # CI brackets the point estimate
    assert -1.0 <= lo <= hi <= 1.0


def test_cli_rejects_underpowered(tmp_path):
    insamp = tmp_path / "in.csv"; oracle = tmp_path / "or.csv"
    ids = list(range(10))  # below default min_n=20
    insamp.write_text("id,s\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    oracle.write_text("id,o\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    proc = _run_cli("--in-sample", str(insamp), "--in-col", "s",
                    "--oracle", str(oracle), "--oracle-col", "o", "--id-col", "id")
    assert proc.returncode != 0
    assert "min" in (proc.stdout + proc.stderr).lower() or "underpowered" in (proc.stdout + proc.stderr).lower()


# ---------------------- regression tests (adversarial review 2026-06-07) ----------------------

def test_regression_duplicate_header_rejected(tmp_path):
    """Duplicate column headers must RAISE, not silently use the last column (corrupts join)."""
    insamp = tmp_path / "in.csv"; oracle = tmp_path / "or.csv"
    insamp.write_text("id,s,id\n1,0.1,3\n2,0.2,1\n3,0.3,2\n")
    oracle.write_text("id,o\n1,0.1\n2,0.2\n3,0.3\n")
    proc = _run_cli("--in-sample", str(insamp), "--in-col", "s",
                    "--oracle", str(oracle), "--oracle-col", "o", "--id-col", "id", "--min-n", "1")
    assert proc.returncode == 2
    assert "duplicate" in (proc.stdout + proc.stderr).lower()


def test_regression_variants_missing_column_clean_error(tmp_path):
    """A --variants CSV missing in_sample_fit/oracle_corr must exit 2, not raise KeyError."""
    insamp = tmp_path / "in.csv"; oracle = tmp_path / "or.csv"; var = tmp_path / "v.csv"
    ids = list(range(25))
    insamp.write_text("id,s\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    oracle.write_text("id,o\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    var.write_text("fit\n0.9\n0.8\n")  # missing both required columns
    proc = _run_cli("--in-sample", str(insamp), "--in-col", "s", "--oracle", str(oracle),
                    "--oracle-col", "o", "--id-col", "id", "--variants", str(var))
    assert proc.returncode == 2, proc.stderr
    assert "Traceback" not in proc.stderr
    assert ("in_sample_fit" in (proc.stdout + proc.stderr)) or ("column" in (proc.stdout + proc.stderr).lower())


def test_regression_n_bootstrap_validated(tmp_path):
    """--n-bootstrap 0 or negative must be rejected up front, not mislabeled 'degenerate data'."""
    insamp = tmp_path / "in.csv"; oracle = tmp_path / "or.csv"
    ids = list(range(25))
    insamp.write_text("id,s\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    oracle.write_text("id,o\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    proc = _run_cli("--in-sample", str(insamp), "--in-col", "s", "--oracle", str(oracle),
                    "--oracle-col", "o", "--id-col", "id", "--n-bootstrap", "0")
    assert proc.returncode == 2
    msg = (proc.stdout + proc.stderr).lower()
    assert "degenerate" not in msg  # must NOT mislabel a bad arg as bad data
    assert "n-bootstrap" in msg or "bootstrap" in msg


def test_regression_unmatched_ids_shows_total(tmp_path):
    """With >10 unmatched ids, the error must indicate the total, not silently show 10."""
    insamp = tmp_path / "in.csv"; oracle = tmp_path / "or.csv"
    insamp.write_text("id,s\n" + "\n".join(f"{i},{i}" for i in range(30)) + "\n")
    oracle.write_text("id,o\n" + "\n".join(f"{i},{i}" for i in range(5)) + "\n")
    proc = _run_cli("--in-sample", str(insamp), "--in-col", "s", "--oracle", str(oracle),
                    "--oracle-col", "o", "--id-col", "id", "--min-n", "1")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 2
    assert "25" in out or "more" in out.lower()  # total count or "and N more"


def test_underpowered_upper_boundary():
    """warn_n upper boundary [30,40): n>=warn_n is NOT underpowered; n=warn_n-1 IS.

    Closes the mutant-survival gap: < warn_n vs <= warn_n at n=30.
    """
    assert clc.power_status(n=29, min_n=20, warn_n=30)["underpowered"] is True
    assert clc.power_status(n=30, min_n=20, warn_n=30)["underpowered"] is False
    assert clc.power_status(n=35, min_n=20, warn_n=40)["underpowered"] is True


def test_cli_metric_pearson(tmp_path):
    """--metric pearson reports a Pearson correlation, not Spearman, and names it."""
    import re
    insamp = tmp_path / "in.csv"; oracle = tmp_path / "or.csv"
    ids = list(range(40))
    insamp.write_text("id,s\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    oracle.write_text("id,o\n" + "\n".join(f"{i},{2*i+1}" for i in ids) + "\n")  # perfectly linear
    proc = _run_cli("--in-sample", str(insamp), "--in-col", "s", "--oracle", str(oracle),
                    "--oracle-col", "o", "--id-col", "id", "--metric", "pearson")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout + proc.stderr
    assert "pearson" in out.lower()
    m = re.search(r"=([-\d.]+)\s+95% CI", out)
    assert m and abs(float(m[1]) - 1.0) < 1e-9  # perfectly linear -> r = 1.0


def test_cli_metric_invalid_rejected(tmp_path):
    """An unknown --metric is rejected loudly (argparse choices)."""
    insamp = tmp_path / "in.csv"; oracle = tmp_path / "or.csv"
    ids = list(range(25))
    insamp.write_text("id,s\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    oracle.write_text("id,o\n" + "\n".join(f"{i},{i}" for i in ids) + "\n")
    proc = _run_cli("--in-sample", str(insamp), "--in-col", "s", "--oracle", str(oracle),
                    "--oracle-col", "o", "--id-col", "id", "--metric", "nonsense")
    assert proc.returncode != 0


def test_bootstrap_ci_different_seeds_differ():
    """Different seeds give different CIs on non-degenerate data (seed is really used).

    Uses range(40)-style near-monotone data (not perfect, so resamples vary). Guards the
    mutant where bootstrap_ci ignores its seed arg and always uses 0.
    """
    x = list(range(40))
    y = [v + (1 if v % 3 == 0 else 0) for v in x]  # non-degenerate
    a = clc.bootstrap_ci(x, y, n_bootstrap=500, seed=1)
    b = clc.bootstrap_ci(x, y, n_bootstrap=500, seed=2)
    assert a != b, "different seeds must produce different CIs (seed must be used)"


def _run_all_in_main():
    import inspect, tempfile
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    for fn in fns:
        if "tmp_path" in inspect.signature(fn).parameters:
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d))
        else:
            fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all_in_main()
