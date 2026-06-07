# falsify-ml diagnostic tests

Tests for the three Gate diagnostics in `skills/falsify/scripts/`:
`planted_signal.py` (Gate 4), `closed_loop_check.py` (Gate 5), `prereg_lock.py` (Gate 2).

The scripts are pure standard library (no numpy/scipy/pandas). The tests run in **two modes** so
they work whether or not pytest is installed — matching the zero-dependency portability goal of the
scripts they cover.

## Run with pytest

```
python3.11 -m pytest tests/ -v
```

(Any Python with `pytest` works; `python3.11` is used here because the machine's default `python3`
has no pytest.)

## Run without pytest (direct execution)

Each test file has an `if __name__ == "__main__"` runner that executes every `test_*` in the file
and prints a pass count. This needs no third-party packages:

```
python3 tests/test_planted_signal.py
python3 tests/test_closed_loop_check.py
python3 tests/test_prereg_lock.py
```

## Test discipline

- AUROC and Spearman assertions check **hand-/oracle-derived values**, not whatever the code
  returns (no tautologies).
- Every test file documents the **manual mutation** that makes its key tests go red
  (CLAUDE.md Part 1 rule 22). The mutations were rehearsed at write time.
- All randomness is **seeded**; the noise AUROC is checked across 12 seeds to rule out flakiness.
