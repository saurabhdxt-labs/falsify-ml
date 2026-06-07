"""Tests for data_reality.py (Stage 1.5 — can the data support the claim?).

Feasibility math is the most dangerous thing to get wrong here: a wrong "you have enough data"
verdict sends someone to spend months on a doomed project. So the power math is checked
bit-accurate against scipy-derived values (validated at authoring time):
  n=20 -> min detectable r 0.59118 ; n=100 -> 0.27703 ; n=300 -> 0.16115
precision_ceiling(0.1) == 0.9 (10% label error caps achievable precision at 0.90).

Manual-mutation rehearsal (CLAUDE.md Part 1 rule 22):
  - perturbing the Fisher-z formula breaks test_min_detectable_r_matches_scipy;
  - flipping the power-verdict comparison breaks test_numbers_mode_power_verdict;
  - dropping the ceiling<required check breaks test_numbers_mode_precision_nogo.
"""

import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "falsify" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import data_reality as dr  # noqa: E402

_SCRIPT = _SCRIPTS_DIR / "data_reality.py"


# ------------------------------ power / feasibility kernels ------------------------------

def test_norm_ppf_matches_scipy_values():
    """Acklam inverse-normal matches known scipy quantiles (drives the power math)."""
    assert abs(dr.norm_ppf(0.975) - 1.959963985) < 1e-6
    assert abs(dr.norm_ppf(0.80) - 0.841621234) < 1e-6
    assert abs(dr.norm_ppf(0.50) - 0.0) < 1e-9


def test_min_detectable_r_matches_scipy():
    """min_detectable_r bit-matches scipy-derived values at several n."""
    assert abs(dr.min_detectable_r(20) - 0.59118) < 1e-4
    assert abs(dr.min_detectable_r(100) - 0.27703) < 1e-4
    assert abs(dr.min_detectable_r(300) - 0.16115) < 1e-4


def test_min_detectable_r_too_small_n_raises():
    try:
        dr.min_detectable_r(3)
    except ValueError:
        pass
    else:
        raise AssertionError("n<4 must raise")


def test_precision_ceiling():
    """10% label error caps achievable precision at 0.90; 0% -> 1.0; 30% -> 0.70."""
    assert abs(dr.precision_ceiling(0.10) - 0.90) < 1e-12
    assert abs(dr.precision_ceiling(0.0) - 1.0) < 1e-12
    assert abs(dr.precision_ceiling(0.30) - 0.70) < 1e-12


def test_precision_ceiling_out_of_range_raises():
    for bad in (-0.1, 1.5):
        try:
            dr.precision_ceiling(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"error rate {bad} must raise")


# ------------------------------ CSV inspection ------------------------------

def test_missingness_and_balance(tmp_path):
    """CSV mode reports n, per-column missingness, and label base rate."""
    csv = tmp_path / "d.csv"
    csv.write_text("id,x,y\n1,1,1\n2,,0\n3,3,1\n4,,0\n5,5,1\n")
    rep = dr.inspect_csv(str(csv), label_col="y")
    assert rep["n"] == 5
    assert abs(rep["missingness"]["x"] - 0.4) < 1e-12  # 2 of 5 blank
    assert abs(rep["base_rate"] - 0.6) < 1e-12  # 3 of 5 positive


def test_gold_disagreement(tmp_path):
    """With a re-labeled gold column, disagreement is the label-noise proxy."""
    csv = tmp_path / "g.csv"
    csv.write_text("id,y,y_gold\n1,1,1\n2,1,0\n3,0,0\n4,0,0\n5,1,1\n")
    rep = dr.inspect_csv(str(csv), label_col="y", gold_col="y_gold")
    assert abs(rep["gold_disagreement"] - 0.2) < 1e-12  # disagree at row 2


# ------------------------------ numbers-mode verdicts ------------------------------

def test_numbers_mode_power_verdict():
    """Detectability verdict: target effect below min-detectable-r at n -> not powered."""
    # n=30 -> min detectable r ~0.49; target 0.4 is below that -> NOT detectable.
    v = dr.power_verdict(n=30, target_effect=0.4)
    assert v["detectable"] is False
    # target 0.6 (> 0.49) -> detectable.
    assert dr.power_verdict(n=30, target_effect=0.6)["detectable"] is True


def test_numbers_mode_precision_nogo():
    """required precision above the label-noise ceiling -> not achievable (DO NOT PURSUE)."""
    v = dr.precision_verdict(label_error_rate=0.10, required_precision=0.95)
    assert v["achievable"] is False and abs(v["ceiling"] - 0.90) < 1e-12
    assert dr.precision_verdict(label_error_rate=0.10, required_precision=0.85)["achievable"] is True


# ------------------------------ CLI ------------------------------

def _run(*args):
    return subprocess.run([sys.executable, str(_SCRIPT), *args], capture_output=True, text=True)


def test_cli_numbers_power(tmp_path):
    proc = _run("--n", "30", "--target-effect", "0.4")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.lower()
    assert "0.49" in out or "not" in out  # reports min-detectable and a verdict


def test_cli_numbers_precision_nogo():
    proc = _run("--label-error-rate", "0.1", "--required-precision", "0.95")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.lower()
    assert "0.90" in out or "0.9" in out
    assert "do not pursue" in out or "not achievable" in out or "below" in out


def test_cli_csv_mode(tmp_path):
    csv = tmp_path / "d.csv"
    csv.write_text("id,x,y\n1,1,1\n2,,0\n3,3,1\n")
    proc = _run("--data", str(csv), "--label-col", "y")
    assert proc.returncode == 0, proc.stderr
    assert "n=3" in proc.stdout or "n = 3" in proc.stdout.lower()


def test_cli_no_inputs_explains():
    """With no data and no numbers, the tool explains what to provide (does not crash)."""
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
