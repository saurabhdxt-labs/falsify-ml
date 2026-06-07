# Worked example — binary classification (spam detector)

A model claims to detect spam. Task shape: **binary classification**, metric **AUROC**.
This walks the falsification stage (Stage 5) end-to-end with the diagnostics, using `--metric auroc`
(the default). Everything here is synthetic and runnable.

## The claim (Stage 5, Gate 1)
> "The spam model's per-message score separates an independent human-labeled spam/not-spam set at
> AUROC ≥ 0.75 on messages it never saw in training."

## Files
- `make_fixtures.py` — generates `model_scores.csv` (id, score, label) and an `oracle.csv`
  (id, human_label) — an *independent* label set joined by id. Pure stdlib, seeded.
- `run.sh` — runs the three gates below.

## Gates (run via `run.sh`, or by hand)

**Gate 4 — prove the ruler (planted signal, AUROC):**
```
python3 ../../skills/falsify/scripts/planted_signal.py --self-test --metric auroc
```
Expect PASS on signal and PASS on noise.

**Gate 4b — score the model's own output:**
```
python3 ../../skills/falsify/scripts/planted_signal.py \
    --scores model_scores.csv --score-col score --labels-col label --metric auroc
```

**Gate 5 — closed-loop check against the independent human oracle:**
```
python3 ../../skills/falsify/scripts/closed_loop_check.py \
    --in-sample model_scores.csv --in-col score \
    --oracle oracle.csv --oracle-col human_label \
    --id-col id --metric spearman
```
A real detector correlates with the independent human labels (CI clears zero). A closed-loop
artifact would score well in-sample but near-zero against the human oracle.

## What this example proves
The same skill that originated in an anomaly-detection project runs unmodified on a spam classifier
— binary labels, AUROC, an independent human-label oracle. No domain assumptions leak in.
