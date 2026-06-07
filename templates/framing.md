# Stage 0 — Problem Framing — <project/claim name>

> Copy this file into your project, fill every field. An unfilled field is an unanswered risk.
> Lifecycle stage 0 of 7. See ../LIFECYCLE.md.

**Date:** <YYYY-MM-DD>

## The decision this model changes
<What downstream decision or action depends on this model's output? If nothing changes
downstream when the model's output changes, STOP — you don't need this model.>

## Success without ML
<Describe what "solved" looks like using NO model — a rule, a lookup table, a human process.
This is your honesty anchor: if the no-ML version is good enough, build that.>

## The trivial heuristic that already exists
<Name the dumbest reasonable baseline for this problem. It becomes your Stage-2 baseline floor.>
- Heuristic: <...>
- Roughly how well does it already do: <...>

## Is the target the right target?
<Is the thing you're predicting what you actually care about, or a convenient proxy? Name the gap
between the proxy and the true goal, and whether optimizing the proxy could hurt the goal.>

## Verdict
- [ ] A real downstream decision depends on this.
- [ ] ML beats the no-ML option enough to be worth it.
- [ ] The target is the right target (or the proxy gap is acceptable and named).

**If any box is unchecked, this project is not ready to consume data or compute.**
