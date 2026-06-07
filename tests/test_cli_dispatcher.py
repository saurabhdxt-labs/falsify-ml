"""Tests for bin/falsify (the standalone CLI dispatcher).

The CLI is the no-Claude front door: it routes subcommands to the six stdlib scripts and passes
their args + exit codes straight through. It must self-locate its scripts (relative to its own
file), so it works from ANY working directory, not just the repo root.

Manual-mutation rehearsal: breaking the subcommand->script map makes the routing tests red;
breaking self-location (hardcoding a wrong dir) makes test_runs_from_foreign_cwd red.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CLI = _ROOT / "bin" / "falsify"


def _run(*args, cwd=None):
    # The dispatcher is a python script; invoke it with the same interpreter for portability.
    return subprocess.run([sys.executable, str(_CLI), *args],
                          capture_output=True, text=True, cwd=cwd)


def test_help_lists_all_subcommands():
    proc = _run("--help")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.lower()
    for sub in ("leakage", "reality", "value", "planted", "closed-loop", "prereg"):
        assert sub in out, f"{sub} missing from --help"


def test_no_args_shows_usage_nonzero():
    proc = _run()
    assert proc.returncode != 0
    assert "usage" in (proc.stdout + proc.stderr).lower()


def test_unknown_subcommand_errors():
    proc = _run("frobnicate")
    assert proc.returncode != 0
    assert "frobnicate" in (proc.stdout + proc.stderr).lower() or \
           "unknown" in (proc.stdout + proc.stderr).lower()


def test_where_prints_repo_root():
    proc = _run("--where")
    assert proc.returncode == 0, proc.stderr
    root = proc.stdout.strip()
    assert (Path(root) / "skills" / "falsify").is_dir()
    assert (Path(root) / "LIFECYCLE.md").is_file()


# ------------------ routing: each subcommand reaches the right script ------------------

def test_route_reality_numbers():
    """`falsify reality ...` routes to data_reality.py and passes flags + exit through."""
    proc = _run("reality", "--label-error-rate", "0.1", "--required-precision", "0.95")
    assert proc.returncode == 0, proc.stderr
    assert "0.90" in proc.stdout or "0.9" in proc.stdout
    assert "do not pursue" in proc.stdout.lower() or "below" in proc.stdout.lower()


def test_route_value_pass():
    proc = _run("value", "--value-per-unit", "50", "--expected-lift", "10000",
                "--deploy-cost", "200000", "--annual-maintenance", "50000")
    assert proc.returncode == 0, proc.stderr
    assert "PASS" in proc.stdout


def test_route_planted_self_test():
    proc = _run("planted", "--self-test", "--seed", "0")
    assert proc.returncode == 0, proc.stderr
    assert "PASS" in proc.stdout


def test_route_passes_exit_code_through():
    """A subcommand that fails (leakage on a leaky CSV) propagates its non-zero exit."""
    with tempfile.TemporaryDirectory() as d:
        csv = Path(d) / "leaky.csv"
        csv.write_text("split,user,y\ntrain,u1,1\ntest,u1,0\ntest,u2,1\n")
        proc = _run("leakage", "--data", str(csv), "--split-col", "split", "--group-col", "user")
        assert proc.returncode != 0  # leak -> non-zero, passed through the dispatcher
        assert "u1" in (proc.stdout + proc.stderr)


def test_subcommand_help_passes_through():
    """`falsify reality --help` shows data_reality's own argparse help, not the dispatcher's."""
    proc = _run("reality", "--help")
    assert proc.returncode == 0, proc.stderr
    assert "--target-effect" in proc.stdout or "--label-error-rate" in proc.stdout


# ------------------ self-location: works from a foreign CWD ------------------

def test_runs_from_foreign_cwd():
    """The dispatcher finds its scripts even when run from an unrelated directory."""
    with tempfile.TemporaryDirectory() as d:
        proc = _run("reality", "--n", "30", "--target-effect", "0.4", cwd=d)
        assert proc.returncode == 0, proc.stderr
        assert "0.49" in proc.stdout or "not" in proc.stdout.lower()


def _run_all_in_main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all_in_main()
