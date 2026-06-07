# Stage 7 — Stopping Rule — <project/claim name>

> Lifecycle stage 7. See ../LIFECYCLE.md.
> Decide what "done" means before you start iterating, or you will iterate forever.

**Date:** <YYYY-MM-DD>

## Stop criteria (pre-committed)
<Concrete, measurable conditions that mean "good enough to stop building.">
- e.g. oracle ρ ≥ <X> AND production drift rate below <Y> for <Z> consecutive periods.
- <...>

## Budget ceiling
- Maximum iteration cycles before escalate/abandon: <...>
- Maximum time/compute budget: <...>
- What happens when the ceiling is hit (escalate to whom? abandon? ship-as-is with caveats?): <...>

## Fragility note (per WORKING verdict)
<For each claim closed WORKING in Stage 5, which assumptions are most likely to go stale, and what
would force you to re-open the hypothesis?>
- Claim: <...>
  - Most fragile assumption: <...>
  - Re-open trigger: <...>

## Verdict
- [ ] Stop criteria committed in writing before iteration.
- [ ] Iteration/time budget ceiling set with a defined consequence.
- [ ] Each WORKING verdict has a named fragile assumption + re-open trigger.

**Without a stopping rule, a project spins in WORKING→tweak→re-measure cycles indefinitely and never
ships — or ships and never revisits a claim that has quietly gone stale.**
