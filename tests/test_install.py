"""Integration tests for install.sh / uninstall.sh (shell scripts are code).

Each test runs the installer with HOME pointed at a throwaway temp dir, so it NEVER touches the
real ~/.claude or ~/.local/bin. Asserts the two symlinks are created, point at the repo, are
idempotent on re-run, refuse to clobber a real (non-symlink) dir, and that uninstall removes them.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_INSTALL = _ROOT / "install.sh"
_UNINSTALL = _ROOT / "uninstall.sh"


def _run_installer(script, home, extra_env=None):
    env = dict(os.environ)
    env["HOME"] = str(home)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env)


def test_install_creates_both_symlinks():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        proc = _run_installer(_INSTALL, home)
        assert proc.returncode == 0, proc.stdout + proc.stderr

        skill = home / ".claude" / "skills" / "falsify"
        cli = home / ".local" / "bin" / "falsify"
        assert skill.is_symlink(), "skill symlink not created"
        assert cli.is_symlink(), "cli symlink not created"
        # they point into the repo
        assert os.path.realpath(skill) == str((_ROOT / "skills" / "falsify").resolve())
        assert os.path.realpath(cli) == str((_ROOT / "bin" / "falsify").resolve())
        # skill is reachable through the symlink
        assert (skill / "SKILL.md").is_file()


def test_install_is_idempotent():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        a = _run_installer(_INSTALL, home)
        b = _run_installer(_INSTALL, home)  # second run must not fail
        assert a.returncode == 0 and b.returncode == 0, a.stdout + b.stdout + b.stderr
        assert (home / ".claude" / "skills" / "falsify").is_symlink()


def test_install_refuses_to_clobber_real_dir():
    """If a REAL directory already sits at the skill target, the installer refuses (no data loss)."""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        real = home / ".claude" / "skills" / "falsify"
        real.mkdir(parents=True)
        (real / "important.txt").write_text("do not delete me")
        proc = _run_installer(_INSTALL, home)
        assert proc.returncode != 0
        assert "refus" in (proc.stdout + proc.stderr).lower() or \
               "exists" in (proc.stdout + proc.stderr).lower()
        # the real file is untouched
        assert (real / "important.txt").read_text() == "do not delete me"


def test_install_notes_path_when_not_on_path():
    """When ~/.local/bin is not on PATH, the installer prints the line to add (doesn't edit rc)."""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        # PATH without ~/.local/bin
        proc = _run_installer(_INSTALL, home, extra_env={"PATH": "/usr/bin:/bin"})
        assert proc.returncode == 0, proc.stdout + proc.stderr
        out = proc.stdout + proc.stderr
        assert ".local/bin" in out and "PATH" in out


def test_installed_cli_runs():
    """After install, the symlinked CLI actually runs a subcommand."""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        _run_installer(_INSTALL, home)
        cli = home / ".local" / "bin" / "falsify"
        proc = subprocess.run([sys.executable, str(cli), "reality",
                               "--label-error-rate", "0.1", "--required-precision", "0.95"],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        assert "0.90" in proc.stdout or "below" in proc.stdout.lower()


def test_uninstall_removes_symlinks():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        _run_installer(_INSTALL, home)
        proc = _run_installer(_UNINSTALL, home)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert not (home / ".claude" / "skills" / "falsify").exists()
        assert not (home / ".local" / "bin" / "falsify").exists()


def test_uninstall_leaves_real_dir_alone():
    """Uninstall must not delete a real dir it didn't create (only removes its own symlinks)."""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        real = home / ".claude" / "skills" / "falsify"
        real.mkdir(parents=True)
        (real / "keep.txt").write_text("keep")
        _run_installer(_UNINSTALL, home)  # should be a no-op on a non-symlink
        assert (real / "keep.txt").read_text() == "keep"


def _run_all_in_main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all_in_main()
