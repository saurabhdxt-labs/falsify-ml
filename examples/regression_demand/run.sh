#!/usr/bin/env bash
# Worked example: regression (demand forecast). Runs the falsification gates with --metric pearson.
# Usage: bash run.sh            (uses python3; set PY=python3.11 to override)
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python3}"
SCRIPTS="../../skills/falsify/scripts"

echo "== generate fixtures =="
"$PY" make_fixtures.py

echo "== Gate 4: prove the ruler (planted signal, Pearson) =="
"$PY" "$SCRIPTS/planted_signal.py" --self-test --metric pearson

echo "== Gate 4b: score the model's own output (pred vs actual) =="
"$PY" "$SCRIPTS/planted_signal.py" \
    --scores predictions.csv --score-col pred --labels-col actual --metric pearson

echo "== Gate 5: closed-loop check vs independent re-measurement =="
"$PY" "$SCRIPTS/closed_loop_check.py" \
    --in-sample predictions.csv --in-col pred \
    --oracle oracle.csv --oracle-col measured_actual \
    --id-col id --metric pearson

echo "== done =="
