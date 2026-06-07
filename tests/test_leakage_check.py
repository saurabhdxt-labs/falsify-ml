"""Tests for leakage_check.py (Stage 1 — leakage / split hygiene).

Four checks; three are HARD failures (exit non-zero), one is a SUSPECT warning:
  - duplicate/identical feature rows spanning train and test  -> hard fail
  - temporal overlap (max train time >= min test time)        -> hard fail
  - group/entity appearing in both splits                     -> hard fail
  - a single feature that perfectly partitions the label      -> SUSPECT (warn, never fail)

Perfect-predictor is deliberately a warning, not a failure: legitimate downstream-consequence
features exist (e.g. pregnant->gave_birth), so it needs human review, not an auto-kill.

Manual-mutation rehearsal: removing any hard-fail check makes its test go red; turning the
perfect-predictor warning into a hard fail makes test_perfect_predictor_is_suspect_not_fail red.
"""

import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "falsify" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import leakage_check as lc  # noqa: E402

_SCRIPT = _SCRIPTS_DIR / "leakage_check.py"


# ------------------------------ unit-level checks ------------------------------

def test_duplicate_rows_across_split_detected():
    """Identical feature rows in both train and test are flagged."""
    rows = [
        {"split": "train", "a": "1", "b": "x"},
        {"split": "test", "a": "1", "b": "x"},   # identical features -> leak
        {"split": "test", "a": "2", "b": "y"},
    ]
    found = lc.check_duplicate_rows(rows, "split", feature_cols=["a", "b"])
    assert found["leak"] is True and found["count"] >= 1


def test_no_duplicate_rows_clean():
    rows = [
        {"split": "train", "a": "1"},
        {"split": "test", "a": "2"},
    ]
    assert lc.check_duplicate_rows(rows, "split", feature_cols=["a"])["leak"] is False


def test_temporal_overlap_detected():
    """max(train time) >= min(test time) is a temporal leak."""
    rows = [
        {"split": "train", "t": "5"},
        {"split": "test", "t": "4"},   # test before train end -> overlap
    ]
    assert lc.check_temporal_overlap(rows, "split", "t")["leak"] is True


def test_temporal_clean():
    rows = [
        {"split": "train", "t": "1"},
        {"split": "train", "t": "2"},
        {"split": "test", "t": "3"},
    ]
    assert lc.check_temporal_overlap(rows, "split", "t")["leak"] is False


def test_group_leakage_detected():
    """A group/entity in both splits is a leak; names the offending group."""
    rows = [
        {"split": "train", "user": "u1"},
        {"split": "test", "user": "u1"},   # same user both sides -> leak
        {"split": "test", "user": "u2"},
    ]
    r = lc.check_group_leakage(rows, "split", "user")
    assert r["leak"] is True and "u1" in r["groups"]


def test_group_clean():
    rows = [
        {"split": "train", "user": "u1"},
        {"split": "test", "user": "u2"},
    ]
    assert lc.check_group_leakage(rows, "split", "user")["leak"] is False


def test_perfect_predictor_is_suspect_not_fail():
    """A feature that perfectly separates the label is a SUSPECT, never a hard fail."""
    rows = [
        {"flag": "1", "y": "1"},
        {"flag": "1", "y": "1"},
        {"flag": "0", "y": "0"},
        {"flag": "0", "y": "0"},
    ]
    r = lc.check_perfect_predictor(rows, "y", feature_cols=["flag"])
    assert r["suspect"] is True and "flag" in r["features"]
    assert r["severity"] == "suspect"  # never "fail"


def test_non_perfect_predictor_quiet():
    rows = [
        {"x": "1", "y": "1"},
        {"x": "1", "y": "0"},
        {"x": "0", "y": "0"},
    ]
    assert lc.check_perfect_predictor(rows, "y", feature_cols=["x"])["suspect"] is False


# ------------------------------ CLI / exit codes ------------------------------

def _run(*args):
    return subprocess.run([sys.executable, str(_SCRIPT), *args], capture_output=True, text=True)


def test_cli_group_leak_exits_nonzero(tmp_path):
    csv = tmp_path / "leaky.csv"
    csv.write_text("split,user,y\ntrain,u1,1\ntest,u1,0\ntest,u2,1\n")
    proc = _run("--data", str(csv), "--split-col", "split", "--group-col", "user")
    assert proc.returncode != 0
    out = proc.stdout + proc.stderr
    assert "u1" in out and "group" in out.lower()


def test_cli_clean_data_exits_zero(tmp_path):
    csv = tmp_path / "clean.csv"
    csv.write_text("split,user,t,y\ntrain,u1,1,1\ntrain,u2,2,0\ntest,u3,3,1\ntest,u4,4,0\n")
    proc = _run("--data", str(csv), "--split-col", "split",
                "--group-col", "user", "--time-col", "t")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_cli_perfect_predictor_warns_but_exits_zero(tmp_path):
    """SUSPECT must NOT change the exit code (it's a warning, not a hard leak)."""
    csv = tmp_path / "suspect.csv"
    csv.write_text("split,flag,y\ntrain,1,1\ntrain,0,0\ntest,1,1\ntest,0,0\n")
    proc = _run("--data", str(csv), "--split-col", "split", "--label-col", "y")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "suspect" in (proc.stdout + proc.stderr).lower()


def test_cli_duplicate_header_loud(tmp_path):
    """Reuse boundary discipline: duplicate headers are a loud error, not silent."""
    csv = tmp_path / "dup.csv"
    csv.write_text("split,a,split\ntrain,1,test\n")
    proc = _run("--data", str(csv), "--split-col", "split")
    assert proc.returncode != 0
    assert "duplicate" in (proc.stdout + proc.stderr).lower()


def test_cli_no_data_explains():
    proc = _run()
    assert proc.returncode == 2
    assert "data" in (proc.stdout + proc.stderr).lower()


def _run_all_in_main():
    import inspect, tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
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
