"""Pytest configuration for the falsify-ml diagnostic test suite.

Adds the skill's `scripts/` directory to sys.path so tests can import the
diagnostic modules (`planted_signal`, `closed_loop_check`, `prereg_lock`)
regardless of the working directory pytest is invoked from.

The same path insertion is duplicated inline in each test file's
`if __name__ == "__main__"` block so the tests also run under a plain
`python3 tests/test_x.py` with no pytest installed (zero-dep portability,
matching the scripts they cover).
"""

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "falsify" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
