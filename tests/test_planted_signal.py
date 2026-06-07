"""Tests for planted_signal.py (Gate 4 — planted-signal meta-falsification).

This script is the most load-bearing in the skill: if its AUROC math is wrong,
every WORKING / NOT WORKING verdict the skill produces is meaningless. So the
AUROC tests check against *hand-computed* values on tiny fixtures, not against
whatever the function happens to return.

Expected AUROC values are derived by hand (see commit notes / plan):
  - separable pos=[.9,.8,.6] neg=[.5,.2,.1]            -> 1.0
  - one inversion pos=[.9,.8,.4] neg=[.5,.2,.1]        -> 8/9
  - ties pos=[.5,.5] neg=[.5,.1]                       -> 0.75

Manual-mutation rehearsal (CLAUDE.md Part 1 rule 22): flipping the U numerator
sign in auroc() (return 1-AUROC) makes test_auroc_separable and
test_auroc_one_inversion go red; removing the average-rank tie handling makes
test_auroc_handles_ties go red.
"""

import math
import subprocess
import sys
from pathlib import Path

# --- path bootstrap so this file runs under both pytest and `python3 thisfile.py` ---
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "falsify" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import planted_signal as ps  # noqa: E402

_SCRIPT = _SCRIPTS_DIR / "planted_signal.py"
_TOL = 1e-12  # exact rational arithmetic on tiny inputs; rounding floor only


# ----------------------------- auroc() correctness -----------------------------

def test_auroc_separable():
    """auroc == 1.0 for perfectly separable scores. Red if U numerator sign flips."""
    scores = [0.9, 0.8, 0.6, 0.5, 0.2, 0.1]
    labels = [1, 1, 1, 0, 0, 0]
    assert abs(ps.auroc(scores, labels) - 1.0) < _TOL


def test_auroc_one_inversion():
    """auroc == 8/9 with a single ranking inversion. Red if U math is wrong."""
    scores = [0.9, 0.8, 0.4, 0.5, 0.2, 0.1]
    labels = [1, 1, 1, 0, 0, 0]
    assert abs(ps.auroc(scores, labels) - (8.0 / 9.0)) < _TOL


def test_auroc_handles_ties():
    """auroc == 0.75 with tied scores via average ranks. Red if ties not averaged."""
    scores = [0.5, 0.5, 0.5, 0.1]
    labels = [1, 1, 0, 0]
    assert abs(ps.auroc(scores, labels) - 0.75) < _TOL


def test_auroc_all_one_class_raises():
    """auroc raises on a single-class label vector (AUROC undefined)."""
    try:
        ps.auroc([0.1, 0.2, 0.3], [1, 1, 1])
    except ValueError as e:
        assert "class" in str(e).lower() or "both" in str(e).lower()
    else:
        raise AssertionError("expected ValueError for single-class labels")


def test_auroc_empty_raises():
    """auroc raises on empty input rather than returning a silent NaN."""
    try:
        ps.auroc([], [])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for empty input")


def test_auroc_length_mismatch_raises():
    """auroc raises when scores and labels differ in length (loud boundary)."""
    try:
        ps.auroc([0.1, 0.2], [1])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for length mismatch")


# ------------------------- self-test signal/noise behavior -------------------------

def test_self_test_detects_signal_and_rejects_noise():
    """run_self_test reports a passing signal AUROC and an in-band noise AUROC."""
    result = ps.run_self_test(n=2000, sigma=10.0, seed=0,
                              auroc_floor=0.99, noise_band=(0.40, 0.60))
    assert result["signal_pass"] is True
    assert result["signal_auroc"] >= 0.99
    assert result["noise_pass"] is True
    assert 0.40 <= result["noise_auroc"] <= 0.60


def test_self_test_noise_stays_in_band_across_seeds():
    """Noise AUROC lands in [0.40,0.60] across 12 seeds at n=2000 (no flakiness).

    Guards against an --n default too small to keep seeded noise in band, which
    would make the self-test intermittently fail (zero-tolerance-for-flaky).
    """
    for seed in range(12):
        r = ps.run_self_test(n=2000, sigma=10.0, seed=seed,
                             auroc_floor=0.99, noise_band=(0.40, 0.60))
        assert 0.40 <= r["noise_auroc"] <= 0.60, (seed, r["noise_auroc"])
        assert r["signal_auroc"] >= 0.99, (seed, r["signal_auroc"])


# ------------------------- metric-aware self-test (regression/ranking) -------------------------

def test_self_test_pearson_detects_and_rejects():
    """run_self_test(metric='pearson') detects a linear planted signal, rejects noise.

    For regression-shaped claims: the planted signal is a strong linear relationship; pure
    noise should give correlation near zero. Generalizes the harness beyond binary AUROC.
    """
    r = ps.run_self_test(n=2000, seed=0, metric="pearson",
                         floor=0.8, noise_band=(-0.1, 0.1))
    assert r["metric"] == "pearson"
    assert r["signal_pass"] is True and r["signal_score"] >= 0.8
    assert r["noise_pass"] is True and -0.1 <= r["noise_score"] <= 0.1


def test_self_test_spearman_detects_and_rejects():
    """run_self_test(metric='spearman') works for monotonic/ranking-shaped claims."""
    r = ps.run_self_test(n=2000, seed=1, metric="spearman",
                         floor=0.8, noise_band=(-0.1, 0.1))
    assert r["metric"] == "spearman"
    assert r["signal_pass"] is True and r["signal_score"] >= 0.8
    assert r["noise_pass"] is True


def test_self_test_auroc_backcompat_keys_present():
    """Default metric stays 'auroc' and the legacy result keys still exist (back-compat)."""
    r = ps.run_self_test(n=2000, seed=0)
    assert r["metric"] == "auroc"
    # legacy keys the existing tests/CLI depend on:
    assert "signal_auroc" in r and "noise_auroc" in r
    # unified keys present for all metrics:
    assert "signal_score" in r and "noise_score" in r


def test_self_test_unknown_metric_raises():
    try:
        ps.run_self_test(metric="nonsense")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown metric must raise")


def test_regression_continuous_labels_accepted_in_pearson_mode(tmp_path):
    """In --metric pearson, continuous targets are NOT rejected (binary-only was too narrow).

    Inverse of the strict 0/1 label rejection: that rejection must be conditional on metric=auroc,
    not unconditional. Red against an unconditional binary-label check.
    """
    csv = tmp_path / "reg.csv"
    csv.write_text("id,s,y\n1,0.1,1.7\n2,0.5,2.9\n3,0.9,4.1\n4,0.3,2.0\n5,0.7,3.5\n")
    proc = _run_cli("--scores", str(csv), "--score-col", "s", "--labels-col", "y",
                    "--metric", "pearson")
    assert proc.returncode == 0, proc.stderr
    assert "pearson" in (proc.stdout + proc.stderr).lower()


def test_cli_self_test_pearson_passes():
    """CLI --self-test --metric pearson exits 0 with PASS on signal and noise."""
    proc = _run_cli("--self-test", "--metric", "pearson", "--seed", "0")
    assert proc.returncode == 0, proc.stderr
    out = (proc.stdout + proc.stderr).lower()
    assert "pass" in out and "pearson" in out


# ------------------------------- CLI behavior -------------------------------

def _run_cli(*args):
    return subprocess.run([sys.executable, str(_SCRIPT), *args],
                          capture_output=True, text=True)


def test_cli_self_test_exits_zero_and_states_scope():
    """--self-test exits 0 and explicitly says it proves the ruler, not the pipeline."""
    proc = _run_cli("--self-test", "--seed", "0")
    assert proc.returncode == 0, proc.stderr
    out = (proc.stdout + proc.stderr).lower()
    assert "pass" in out
    # Must not let "self-test passed" read as "your pipeline works".
    assert "pipeline" in out and ("not" in out or "math" in out or "ruler" in out)


def test_cli_scores_without_score_col_errors_loudly():
    """--scores given without --score-col is a loud non-zero error (review #2)."""
    csv = _SCRIPTS_DIR.parent / "scripts"  # any path; CLI must error before reading
    proc = _run_cli("--scores", str(csv), "--labels-col", "y")
    assert proc.returncode != 0
    assert "score-col" in (proc.stdout + proc.stderr).lower()


def test_cli_scores_mode_computes_auroc(tmp_path):
    """--scores mode reads a CSV and reports the AUROC of the user's own output."""
    csv = tmp_path / "scored.csv"
    csv.write_text(
        "id,s,y\n"
        "1,0.9,1\n2,0.8,1\n3,0.6,1\n4,0.5,0\n5,0.2,0\n6,0.1,0\n"
    )
    proc = _run_cli("--scores", str(csv), "--score-col", "s", "--labels-col", "y")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout + proc.stderr
    assert "1.0" in out or "1.000" in out  # separable -> AUROC 1.0


# ---------------------- regression tests (adversarial review 2026-06-07) ----------------------
# Each guards a confirmed boundary bug found by the multi-agent falsify-final-review.

def test_regression_fractional_label_rejected(tmp_path):
    """Fractional labels (0.5) must RAISE, not silently truncate to 0/1 and corrupt AUROC.

    Red against int(float(...)) truncation: '0.5'->0, '1.5'->1 flipped labels silently.
    """
    csv = tmp_path / "frac.csv"
    csv.write_text("id,s,y\n1,0.9,1\n2,0.8,0.5\n3,0.2,0\n")
    proc = _run_cli("--scores", str(csv), "--score-col", "s", "--labels-col", "y")
    assert proc.returncode != 0, "fractional label must be a loud error"
    assert "0.5" in (proc.stdout + proc.stderr) or "binary" in (proc.stdout + proc.stderr).lower()


def test_regression_inf_label_clean_error(tmp_path):
    """An 'inf' label must produce a clean ERROR + exit 2, not an OverflowError traceback."""
    csv = tmp_path / "inf.csv"
    csv.write_text("id,s,y\n1,0.5,0\n2,0.7,inf\n")
    proc = _run_cli("--scores", str(csv), "--score-col", "s", "--labels-col", "y")
    assert proc.returncode == 2, "inf label must exit 2 (clean), not crash"
    assert "Traceback" not in proc.stderr
    assert "ERROR" in (proc.stdout + proc.stderr)


def test_regression_duplicate_header_rejected(tmp_path):
    """Duplicate column headers must RAISE, not silently use the last occurrence."""
    csv = tmp_path / "dup.csv"
    csv.write_text("s,y,s\n0.5,0,0.9\n0.7,1,0.8\n")
    proc = _run_cli("--scores", str(csv), "--score-col", "s", "--labels-col", "y")
    assert proc.returncode == 2
    assert "duplicate" in (proc.stdout + proc.stderr).lower()


def test_regression_n_zero_clean_error():
    """--n 0 (and --n 1) must exit 2 cleanly, not raise an uncaught ValueError."""
    for n in ("0", "1"):
        proc = _run_cli("--self-test", "--n", n)
        assert proc.returncode == 2, f"--n {n} must exit 2"
        assert "Traceback" not in proc.stderr


def test_regression_auroc_floor_out_of_range():
    """--auroc-floor outside [0,1] must be rejected (it can only be vacuously true/false)."""
    proc = _run_cli("--self-test", "--auroc-floor", "2.0")
    assert proc.returncode == 2
    proc2 = _run_cli("--self-test", "--auroc-floor", "-1.0")
    assert proc2.returncode == 2


def test_regression_noise_band_invalid():
    """--noise-band must reject inverted (1.0,0.5) and out-of-range (-5,5) bands."""
    for band in ("1.0,0.5", "-5.0,5.0"):
        proc = _run_cli("--self-test", "--noise-band", band)
        assert proc.returncode == 2, f"band {band} must be rejected"


def test_parse_label_helper_rejects_nonbinary():
    """The label parser rejects fractional, inf, nan, and out-of-range values (unit-level)."""
    assert ps.parse_label("0") == 0
    assert ps.parse_label("1") == 1
    assert ps.parse_label("1.0") == 1  # exact-integer float is fine
    for bad in ("0.5", "1.5", "2", "-1", "inf", "-inf", "nan", "banana"):
        try:
            ps.parse_label(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"parse_label should reject {bad!r}")


def _run_all_in_main():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    import inspect
    for fn in fns:
        sig = inspect.signature(fn)
        if "tmp_path" in sig.parameters:
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d))
        else:
            fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all_in_main()
