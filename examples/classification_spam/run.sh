#!/usr/bin/env bash
# Worked example: binary classification (spam). Runs the falsification gates end-to-end.
# Usage: bash run.sh            (uses python3; set PY=python3.11 to override)
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python3}"
SCRIPTS="../../skills/falsify/scripts"

echo "== generate fixtures =="
"$PY" make_fixtures.py

echo "== Gate 4: prove the ruler (planted signal, AUROC) =="
"$PY" "$SCRIPTS/planted_signal.py" --self-test --metric auroc

echo "== Gate 4b: score the model's own output =="
"$PY" "$SCRIPTS/planted_signal.py" \
    --scores model_scores.csv --score-col score --labels-col label --metric auroc

echo "== Gate 5: closed-loop check vs independent human oracle =="
"$PY" "$SCRIPTS/closed_loop_check.py" \
    --in-sample model_scores.csv --in-col score \
    --oracle oracle.csv --oracle-col human_label \
    --id-col id --metric spearman

echo "== done =="
