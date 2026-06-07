# Worked example — regression (demand forecast)

A model claims to predict next-week demand. Task shape: **regression**, metric **Pearson**.
This proves the skill is not binary-classification-only: the same gates run with `--metric pearson`.
Everything here is synthetic and runnable.

## The claim (Stage 5, Gate 1)
> "The forecast's predicted demand tracks the held-out actual demand at Pearson r ≥ 0.6 on a
> period after everything it trained on."

## Files
- `make_fixtures.py` — generates `predictions.csv` (id, pred, actual) and `oracle.csv`
  (id, measured_actual) — an independent re-measurement of actual demand, joined by id. Seeded stdlib.
- `run.sh` — runs the gates below.

## Gates

**Gate 4 — prove the ruler (planted signal, Pearson):**
```
python3 ../../skills/falsify/scripts/planted_signal.py --self-test --metric pearson
```
Expect PASS on a strong linear planted signal and PASS on noise (r ≈ 0).

**Gate 4b — score the model's own output (pred vs actual):**
```
python3 ../../skills/falsify/scripts/planted_signal.py \
    --scores predictions.csv --score-col pred --labels-col actual --metric pearson
```
Note: continuous targets — they are NOT rejected here, because the metric is `pearson`, not `auroc`.

**Gate 5 — closed-loop check vs an independent re-measurement of actual demand:**
```
python3 ../../skills/falsify/scripts/closed_loop_check.py \
    --in-sample predictions.csv --in-col pred \
    --oracle oracle.csv --oracle-col measured_actual \
    --id-col id --metric pearson
```

## What this example proves
A regression task — continuous predictions, continuous targets, Pearson correlation — runs through
the identical falsification skill. The `--metric` flag is the only thing that changes versus the
classification example. The methodology is task-agnostic.
