# Stage 2 — Baseline Before Training — <project/claim name>

> Lifecycle stage 2. See ../LIFECYCLE.md.
> Fill this BEFORE training. The point is to lock the bar before a result can bias it.

**Date:** <YYYY-MM-DD>  (must predate the first training run)

## Baselines measured
<Measure these on the SAME held-out set you'll evaluate the model on.>
| Baseline | Metric value |
|----------|--------------|
| Random / chance | <...> |
| Majority-class or last-value-carried-forward | <...> |
| Dumbest domain heuristic (from Stage 0 framing) | <...> |
| Free public tool/data that already does this (if any) | <...> |

## Minimum marginal lift to justify the model
<The model must beat the BEST baseline above by at least this much to be worth building.
Commit the number now — it's the bar Stage 5 must clear.>
- Required lift over best baseline: <e.g. +5 AUROC points / -20% MAE / +0.1 rank-corr>
- Why that number is the threshold of "worth it": <...>

## Achievability cross-check
- Best baseline + required lift = target performance: <...>
- Stage 1.5 said the achievable ceiling is: <...>
- Is the target below the ceiling (i.e. possible)? <yes/no>

## Verdict
- [ ] All relevant baselines measured on the real eval set.
- [ ] Minimum lift committed in writing, before training.
- [ ] Target (baseline + lift) is below the Stage-1.5 ceiling.

**If the free/trivial baseline already meets the need, the model's marginal value may be zero —
that is a valid and money-saving STOP.**
