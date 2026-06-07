"""Tests for prereg_lock.py (Gate 2 — date-locked pre-registration).

The lock guarantee tested here is: a dated file is written with all three
sections, the content is SHA-256 hashed, and a second write for the SAME date
is refused (a changed threshold must become a NEW dated file). None of these
assertions depend on a .git directory existing (review #7) — git history is an
additional visibility layer once the file is committed, not a precondition.

Manual-mutation rehearsal (CLAUDE.md Part 1 rule 22):
  - removing the overwrite-refusal check breaks test_refuses_same_date_overwrite;
  - making the hash ignore content breaks test_hash_changes_with_content;
  - dropping a section from the template breaks test_writes_all_three_sections.
"""

import datetime as dt
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "falsify" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import prereg_lock as pl  # noqa: E402

_SCRIPT = _SCRIPTS_DIR / "prereg_lock.py"
_FIXED_DAY = dt.date(2026, 6, 7)


def test_parse_thresholds_ok():
    assert pl.parse_thresholds("rho=0.4;auroc=0.75") == {"rho": "0.4", "auroc": "0.75"}


def test_parse_thresholds_malformed_raises():
    """A threshold spec without '=' is a loud error, not a silent drop."""
    try:
        pl.parse_thresholds("rho 0.4")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for malformed thresholds")


def test_writes_all_three_sections(tmp_path):
    """The locked file contains TRUE shape, FALSE shape, and thresholds."""
    res = pl.write_prereg(
        slug="demo", true_shape="rho>0.4 if real", false_shape="rho~0 if closed loop",
        thresholds={"rho": "0.4"}, out_dir=tmp_path, today=_FIXED_DAY)
    text = Path(res["path"]).read_text()
    assert "TRUE shape" in text and "rho>0.4 if real" in text
    assert "FALSE shape" in text and "rho~0 if closed loop" in text
    assert "rho" in text and "0.4" in text


def test_filename_is_dated(tmp_path):
    res = pl.write_prereg(slug="demo", true_shape="t", false_shape="f",
                          thresholds={"k": "1"}, out_dir=tmp_path, today=_FIXED_DAY)
    assert Path(res["path"]).name == "prereg_2026-06-07.md"


def test_refuses_same_date_overwrite(tmp_path):
    """A second write for the same date is refused (goalpost-moving must be a new file)."""
    pl.write_prereg(slug="demo", true_shape="t", false_shape="f",
                    thresholds={"k": "1"}, out_dir=tmp_path, today=_FIXED_DAY)
    try:
        pl.write_prereg(slug="demo", true_shape="t2", false_shape="f2",
                        thresholds={"k": "2"}, out_dir=tmp_path, today=_FIXED_DAY)
    except FileExistsError as e:
        assert "2026-06-07" in str(e)
    else:
        raise AssertionError("expected FileExistsError on same-date overwrite")


def test_hash_is_stable_for_identical_content(tmp_path):
    a = pl.content_hash("alpha")
    b = pl.content_hash("alpha")
    assert a == b and len(a) == 64  # sha256 hex


def test_hash_changes_with_content():
    assert pl.content_hash("alpha") != pl.content_hash("alpha ")


def test_hash_is_actually_sha256():
    """Pin the algorithm to SHA-256 by known-answer test.

    Strengthened after the adversarial review: a stable 64-char hash could be
    MD5().hexdigest().ljust(64,'0') and still pass the stability+length checks.
    The git-history audit story depends on it being real SHA-256.
    """
    assert pl.content_hash("alpha") == \
        "8ed3f6ad685b959ead7022518e1af76cd816f8e8ec7ccdda1ed4018e8f2223f8"


def test_regression_ondisk_trailer_matches_body_hash(tmp_path):
    """The SHA-256 trailer written into the file must equal the hash of the body.

    Guards the mutant where content_hash() is correct but the trailer write is
    corrupted — the on-disk lock proof would be wrong yet invisible to every
    text-only assertion.
    """
    res = pl.write_prereg(slug="demo", true_shape="t", false_shape="f",
                          thresholds={"rho": "0.4"}, out_dir=tmp_path, today=_FIXED_DAY)
    full = Path(res["path"]).read_text()
    # the file is: body + "\n<!-- sha256: <digest> -->\n"
    import re
    m = re.search(r"<!-- sha256: ([0-9a-f]{64}) -->", full)
    assert m, "no sha256 trailer found on disk"
    on_disk_digest = m.group(1)
    body = full[: full.index("\n<!-- sha256:")]
    assert on_disk_digest == pl.content_hash(body)
    assert on_disk_digest == res["sha256"]


def test_cli_writes_and_refuses_rerun(tmp_path):
    """End-to-end: writes a dated file + prints hash; same-day rerun exits non-zero."""
    out = tmp_path / "out"
    args = ["--slug", "demo", "--true-shape", "t", "--false-shape", "f",
            "--thresholds", "rho=0.4", "--out-dir", str(out)]
    p1 = subprocess.run([sys.executable, str(_SCRIPT), *args], capture_output=True, text=True)
    assert p1.returncode == 0, p1.stderr
    assert "sha256" in (p1.stdout + p1.stderr).lower()
    files = list(out.glob("prereg_*.md"))
    assert len(files) == 1
    p2 = subprocess.run([sys.executable, str(_SCRIPT), *args], capture_output=True, text=True)
    assert p2.returncode != 0  # refuses same-date overwrite


def test_cli_file_inputs(tmp_path):
    """--*-file inputs read long text from files (review #6)."""
    ts = tmp_path / "ts.txt"; ts.write_text("a long\nmulti-line true shape\n")
    out = tmp_path / "out"
    p = subprocess.run(
        [sys.executable, str(_SCRIPT), "--slug", "demo", "--true-shape-file", str(ts),
         "--false-shape", "f", "--thresholds", "rho=0.4", "--out-dir", str(out)],
        capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    text = list(out.glob("prereg_*.md"))[0].read_text()
    assert "multi-line true shape" in text


def test_cli_inline_and_file_conflict_errors(tmp_path):
    """Passing both --true-shape and --true-shape-file is a loud error."""
    ts = tmp_path / "ts.txt"; ts.write_text("x")
    p = subprocess.run(
        [sys.executable, str(_SCRIPT), "--slug", "demo", "--true-shape", "inline",
         "--true-shape-file", str(ts), "--false-shape", "f",
         "--thresholds", "rho=0.4", "--out-dir", str(tmp_path / "o")],
        capture_output=True, text=True)
    assert p.returncode != 0
    assert "true-shape" in (p.stdout + p.stderr).lower()


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
