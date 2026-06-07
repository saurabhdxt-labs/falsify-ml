# Stage 3 — Training Health — <project/claim name>

> Lifecycle stage 3. See ../LIFECYCLE.md.

**Date:** <YYYY-MM-DD>  **Run id / checkpoint:** <...>

## Convergence
- Did the loss/metric converge, or is it still moving / NaN / diverging? <...>
- Attach or link the loss curve: <path/url>

## Per-sample loss sanity
- Is the per-sample loss distribution sane, or is one cohort failing predictably? <...>
- Worst-cohort check (slice by a key dimension): <...>

## In-flight guards
<Were there runtime guards against NaN/Inf loss and gradient spikes? A run without guards can
diverge silently for hours.>
- NaN/Inf abort guard present: <yes/no>
- Gradient-spike / loss-spike abort guard present: <yes/no>
- Link to project training guards (if any): <...>

## Overfitting
- Train metric vs. validation metric gap: <...>
- Is the gap acceptable for the claim, or is the model memorizing? <...>

## Verdict
- [ ] Converged (not still-moving, not NaN, not diverging).
- [ ] Per-sample loss sane; no silently-failing cohort.
- [ ] In-flight numerical guards were active (or absence is named as accepted risk).
- [ ] Train/val gap acceptable.

**A model that converged to noise will still produce a confident-looking number in Stage 5. Catch it
here.**
