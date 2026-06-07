#!/usr/bin/env python3
"""Generate synthetic fixtures for the regression (demand-forecast) worked example.

Pure stdlib, seeded. Writes:
  predictions.csv : id, pred, actual          (model prediction + true actual demand)
  oracle.csv      : id, measured_actual        (independent re-measurement of actual, joined by id)

The model tracks actual demand with real but imperfect correlation; the oracle re-measures actual
demand with its own small noise (independent instrument). Run: python3 make_fixtures.py
"""

import csv
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(seed=0, n=300):
    rng = random.Random(seed)
    pred_rows, oracle_rows = [], []
    for i in range(n):
        actual = rng.gauss(100.0, 25.0)          # true demand
        pred = actual + rng.gauss(0.0, 18.0)      # model: correlated but imperfect
        measured = actual + rng.gauss(0.0, 5.0)   # oracle: independent re-measurement
        pred_rows.append({"id": i, "pred": round(pred, 3), "actual": round(actual, 3)})
        oracle_rows.append({"id": i, "measured_actual": round(measured, 3)})

    with open(HERE / "predictions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "pred", "actual"])
        w.writeheader(); w.writerows(pred_rows)
    with open(HERE / "oracle.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "measured_actual"])
        w.writeheader(); w.writerows(oracle_rows)
    print(f"wrote {n} rows to predictions.csv and oracle.csv (seed={seed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
