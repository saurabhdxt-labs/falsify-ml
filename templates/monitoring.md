# Stage 6 — Deploy + Monitor Drift — <project/claim name>

> Lifecycle stage 6 of 7. See ../LIFECYCLE.md.
> A model that passed Stage 5 can still rot in production. This stage is how you notice.

**Date:** <YYYY-MM-DD>

## What "drift" means for THIS model
<Be concrete — pick the observable signals you will actually watch.>
- Feature-distribution shift (which features, what statistic): <...>
- Output/score distribution shift: <...>
- Drop in oracle correlation (re-running the Stage-5 oracle in prod): <...>
- Rise in a guardrail metric (e.g. error rate, calibration error): <...>

## Alert thresholds
| Signal | Threshold | Who/what watches it |
|--------|-----------|---------------------|
| <...> | <...> | <...> |

## Retrain vs. roll back
- Condition that triggers a **retrain**: <...>
- Condition that triggers a **rollback**: <...>
- Who decides / what automation acts: <...>

## Oracle re-run cadence
<The Stage-5 oracle test is not a one-time launch gate. How often is it re-run on fresh prod data?>
- Cadence: <e.g. weekly / per-1000-predictions / monthly>

## Verdict
- [ ] Drift is defined concretely with named observable signals.
- [ ] Alert thresholds set and owned.
- [ ] Retrain and rollback triggers defined.
- [ ] Oracle re-run cadence scheduled, not one-time.

**"We shipped WORKING" is not "it's still working six months later." This stage closes that gap.**
