# Stage 1 — Data Contract + Leakage — <project/claim name>

> Lifecycle stage 1. See ../LIFECYCLE.md. This stage asks "is the data CLEAN?"
> (Stage 1.5 asks the separate question "is the signal even PRESENT?")

**Date:** <YYYY-MM-DD>

## Label definition
<How is the label defined? Is the definition consistent across the whole data source?>
- If human-labeled: inter-rater agreement (Cohen's κ / % agreement): <...>
- Any label-definition drift across time/source: <...>

## Train/test split hygiene
- Split type: <temporal | grouped-by-entity | random row order>
- **If random:** justify why rows are independent. Random splits LEAK when rows share an entity,
  session, or time window. <...>
- Are there duplicate or near-duplicate rows spanning the split? How checked: <...>

## Leakage audit (features)
<For each feature, is every value available AT PREDICTION TIME for a real future instance?>
- Features that encode future information or the target itself: <none | list>
- How leakage was checked (e.g. ablate-and-watch-AUROC, time-of-availability audit): <...>

## Verdict
- [ ] Label definition consistent (and agreement measured if human-labeled).
- [ ] Split is temporal/grouped, or random-split independence is justified.
- [ ] No future-info / target leakage in features.
- [ ] No duplicate rows spanning the split.

**If any box is unchecked, any metric you compute downstream may be measuring leakage, not skill.**
