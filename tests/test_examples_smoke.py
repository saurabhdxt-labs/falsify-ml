"""Smoke test: the worked examples run end-to-end to exit 0.

Examples are runnable code (per "every file that runs has a test"), so each example's full
gate sequence is executed here. The examples double as proof the skill is task-agnostic:
classification_spam uses --metric auroc; regression_demand uses --metric pearson.

Each example is run by invoking its commands directly (not via bash run.sh) so the test is
portable and doesn't depend on a shell — but run.sh mirrors exactly these commands.
"""

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "skills" / "falsify" / "scripts"
_PLANTED = _SCRIPTS / "planted_signal.py"
_CLOSED = _SCRIPTS / "closed_loop_check.py"


def _run(*args, cwd=None):
    return subprocess.run([sys.executable, *map(str, args)],
                          capture_output=True, text=True, cwd=cwd)


def test_classification_example_runs():
    """classification_spam: fixtures + AUROC self-test + scores mode + closed-loop, all exit 0."""
    ex = _ROOT / "examples" / "classification_spam"
    assert _run(ex / "make_fixtures.py", cwd=ex).returncode == 0
    assert _run(_PLANTED, "--self-test", "--metric", "auroc").returncode == 0
    p = _run(_PLANTED, "--scores", ex / "model_scores.csv",
             "--score-col", "score", "--labels-col", "label", "--metric", "auroc")
    assert p.returncode == 0, p.stderr
    c = _run(_CLOSED, "--in-sample", ex / "model_scores.csv", "--in-col", "score",
             "--oracle", ex / "oracle.csv", "--oracle-col", "human_label",
             "--id-col", "id", "--metric", "spearman")
    assert c.returncode == 0, c.stderr
    assert "spearman" in (c.stdout + c.stderr).lower()


def test_regression_example_runs():
    """regression_demand: fixtures + Pearson self-test + scores mode + closed-loop, all exit 0.

    Continuous targets must be accepted in pearson mode (the key non-binary proof).
    """
    ex = _ROOT / "examples" / "regression_demand"
    assert _run(ex / "make_fixtures.py", cwd=ex).returncode == 0
    assert _run(_PLANTED, "--self-test", "--metric", "pearson").returncode == 0
    p = _run(_PLANTED, "--scores", ex / "predictions.csv",
             "--score-col", "pred", "--labels-col", "actual", "--metric", "pearson")
    assert p.returncode == 0, p.stderr  # continuous targets NOT rejected
    assert "pearson" in (p.stdout + p.stderr).lower()
    c = _run(_CLOSED, "--in-sample", ex / "predictions.csv", "--in-col", "pred",
             "--oracle", ex / "oracle.csv", "--oracle-col", "measured_actual",
             "--id-col", "id", "--metric", "pearson")
    assert c.returncode == 0, c.stderr


def _run_all_in_main():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all_in_main()
