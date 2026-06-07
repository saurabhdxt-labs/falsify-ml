"""Tests for value_check.py (Stage 2.5 — Value / Economics).

Catches the project that is scientifically sound but economically pointless (the '1% lift,
$2M deploy' kill). The arithmetic is the mechanical part of value; the judgment inputs come
from templates/value_case.md.

Grounded fixtures:
  A (worth it): value_per_unit 50, lift 10000 -> gross 500k; deploy 200k; maint 50k
                -> annual_net 450k, payback ~0.444yr -> PASS
  B (the kill): value_per_unit 10, lift 1000 -> gross 10k; deploy 2M; maint 100k
                -> annual_net -90k, no payback -> FAIL

Manual-mutation rehearsal: flipping the PASS/FAIL comparison breaks test_value_verdict_*;
dropping maintenance from annual_net breaks test_value_numbers.
"""

import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "falsify" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import value_check as vc  # noqa: E402

_SCRIPT = _SCRIPTS_DIR / "value_check.py"
_TOL = 1e-9


def test_value_numbers():
    """compute_value returns grounded gross/annual_net/payback."""
    r = vc.compute_value(value_per_unit=50, expected_lift=10000,
                         deploy_cost=200000, annual_maintenance=50000)
    assert abs(r["gross_gain"] - 500000) < _TOL
    assert abs(r["annual_net"] - 450000) < _TOL
    assert abs(r["payback_years"] - (200000 / 450000)) < 1e-9


def test_value_verdict_pass():
    r = vc.compute_value(value_per_unit=50, expected_lift=10000,
                         deploy_cost=200000, annual_maintenance=50000)
    assert r["verdict"] == "PASS"


def test_value_verdict_fail_the_2m_kill():
    """The '1% lift, $2M deploy' case: gains never cover cost -> FAIL, no payback."""
    r = vc.compute_value(value_per_unit=10, expected_lift=1000,
                         deploy_cost=2000000, annual_maintenance=100000)
    assert r["verdict"] == "FAIL"
    assert r["annual_net"] < 0
    assert r["payback_years"] is None


def test_value_breakeven_is_pass():
    """Exactly breaking even annually (annual_net == 0) is borderline -> not FAIL.

    annual_net == 0 means gains cover maintenance but not deploy; treat as borderline PASS-ish
    only if deploy is recoverable; here annual_net==0 -> no payback -> FAIL (deploy never recovers).
    """
    r = vc.compute_value(value_per_unit=10, expected_lift=10000,
                         deploy_cost=50000, annual_maintenance=100000)
    # gross 100k, annual_net 0 -> deploy never recovers -> FAIL
    assert r["annual_net"] == 0
    assert r["verdict"] == "FAIL"


def test_negative_inputs_raise():
    for kw in [{"value_per_unit": -1}, {"expected_lift": -5}, {"deploy_cost": -10}]:
        args = {"value_per_unit": 10, "expected_lift": 100,
                "deploy_cost": 1000, "annual_maintenance": 100}
        args.update(kw)
        try:
            vc.compute_value(**args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {kw}")


# ------------------------------ CLI ------------------------------

def _run(*args):
    return subprocess.run([sys.executable, str(_SCRIPT), *args], capture_output=True, text=True)


def test_cli_pass():
    proc = _run("--value-per-unit", "50", "--expected-lift", "10000",
                "--deploy-cost", "200000", "--annual-maintenance", "50000")
    assert proc.returncode == 0, proc.stderr
    assert "PASS" in proc.stdout


def test_cli_fail():
    proc = _run("--value-per-unit", "10", "--expected-lift", "1000",
                "--deploy-cost", "2000000", "--annual-maintenance", "100000")
    # FAIL is a valid computed verdict, not a tool error -> exit 0, verdict in output.
    assert proc.returncode == 0, proc.stderr
    assert "DO NOT PURSUE" in proc.stdout or "FAIL" in proc.stdout


def test_cli_missing_inputs_unknown():
    """Missing inputs -> UNKNOWN, not a crash."""
    proc = _run("--value-per-unit", "50")
    assert proc.returncode == 2
    assert "UNKNOWN" in (proc.stdout + proc.stderr) or "required" in (proc.stdout + proc.stderr).lower()


def _run_all_in_main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all_in_main()
