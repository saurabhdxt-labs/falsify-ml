# Stage 4 — Eval Design — <project/claim name>

> Lifecycle stage 4. See ../LIFECYCLE.md.
> Decide these BEFORE looking at results, then lock them in Stage 5's pre-registration.

**Date:** <YYYY-MM-DD>

## Metric choice (justify, don't default)
- Task shape: <binary classification | regression | ranking | other>
- Chosen metric: <AUROC | Pearson | RMSE | Spearman | NDCG | ...>
- **Why this metric for this task and decision?** <...>
- What the metric does NOT capture (and why that's acceptable here): <...>

> Metric ↔ `--metric` flag for the diagnostics:
> classification → `auroc`; regression → `pearson`; monotonic/ranking → `spearman`.

## Statistical power
- Evaluation sample size n: <...>
- Effect size that matters (minimum meaningful difference): <...>
- Is n large enough to detect that effect? <yes/no + reasoning or power calc>

## Confidence intervals
- CI method: <non-parametric percentile bootstrap | other>
- Bootstrap N (and evidence the CI width has converged at that N): <...>
- Fixed seed for reproducibility: <...>

## Lock
- [ ] Metric chosen and justified before seeing results.
- [ ] Power checked: n is adequate for the effect size.
- [ ] CI method + bootstrap N + seed fixed.
- [ ] These will be written verbatim into the Stage-5 pre-registration (prereg_lock.py).

**A metric chosen after seeing results is p-hacking with extra steps.**
