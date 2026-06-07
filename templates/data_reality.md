# Stage 1.5 — Data Reality Check — <project/claim name>

> Lifecycle stage 1.5 of 7. See ../LIFECYCLE.md.
> The question here is NOT "is the data clean?" (Stage 1) — it is "can the data PHYSICALLY support
> the claim at all?" A perfectly clean dataset can still be unable to support the model you want.

**Date:** <YYYY-MM-DD>

## Sample size vs. required effect
- Total examples: <N>  (positives / negatives or target distribution: <...>)
- Effect size you need to detect (from Stage 4 power, or estimate now): <...>
- Is N large enough to detect that effect above noise? <yes/no + reasoning>

## Label-noise floor
<If labels are X% wrong, achievable precision/accuracy is capped regardless of the model.>
- Estimated label error rate: <X%> (how estimated: <...>)
- Implied ceiling on the target metric: <...>
- Does the claim's required performance sit BELOW that ceiling? <yes/no>

## Missingness
- Missingness rate per key feature: <...>
- Missing-at-random or systematic? <...> (systematic missingness can itself leak or bias)

## Target stability over time
<Does the relationship you're learning hold still long enough to learn and deploy it?>
- How fast does the target/relationship drift: <...>
- Is learn-and-deploy faster than the drift? <yes/no>

## Irreducible uncertainty (Bayes-error ceiling)
<What is the best ANY model could do here? Are you chasing a ceiling physics/labels forbid?>
- Estimated irreducible error: <...>
- Is the claim's target above that ceiling (i.e. achievable)? <yes/no>

## Verdict
- [ ] Enough examples for the required effect size.
- [ ] Required performance sits below the label-noise ceiling (achievable).
- [ ] Missingness understood and not silently biasing.
- [ ] Target stable enough to learn-and-deploy.
- [ ] Claim target is above the irreducible-uncertainty floor.

**If any box is unchecked, training may be doomed before it starts — no model can beat a ceiling the
data imposes. This is the cheapest place to kill a hopeless project.**
