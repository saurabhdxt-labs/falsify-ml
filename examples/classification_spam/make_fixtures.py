#!/usr/bin/env python3
"""Generate synthetic fixtures for the classification (spam) worked example.

Pure stdlib, seeded. Writes:
  model_scores.csv : id, score, label   (the model's output + true binary label)
  oracle.csv       : id, human_label     (an INDEPENDENT human label set, joined by id)

The model is decent-but-not-perfect; the human oracle agrees with the truth most of the time
but not always (independent measurement, its own noise). Run: python3 make_fixtures.py
"""

import csv
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(seed=0, n=300):
    rng = random.Random(seed)
    scores_rows, oracle_rows = [], []
    for i in range(n):
        is_spam = 1 if rng.random() < 0.4 else 0
        # Model score: higher for spam, with overlap (AUROC well below 1.0).
        score = rng.gauss(0.65 if is_spam else 0.35, 0.18)
        score = max(0.0, min(1.0, score))
        scores_rows.append({"id": i, "score": round(score, 4), "label": is_spam})
        # Independent human oracle: agrees with truth ~85% of the time.
        human = is_spam if rng.random() < 0.85 else 1 - is_spam
        oracle_rows.append({"id": i, "human_label": human})

    with open(HERE / "model_scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "score", "label"])
        w.writeheader(); w.writerows(scores_rows)
    with open(HERE / "oracle.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "human_label"])
        w.writeheader(); w.writerows(oracle_rows)
    print(f"wrote {n} rows to model_scores.csv and oracle.csv (seed={seed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
