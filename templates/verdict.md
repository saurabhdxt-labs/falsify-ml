# Stage 5 — Verdict Card — <claim slug>

> Lifecycle stage 5 (the falsification deep dive). See ../PROTOCOL.md and the /falsify skill.
> One verdict per card, dated. No "probably," "partially," "directionally," or "tests pass."

**Date:** <YYYY-MM-DD>  **Hypothesis slug:** <kebab-case>

## Hypothesis (one sentence, one measurable outcome)
<...>

## Pre-registered shapes (from prereg_lock.py — cite the dated file)
- Pre-registration file: `falsify/<slug>/prereg_<DATE>.md`  (sha256: <...>)
- TRUE shape: <...>
- FALSE shape: <...>
- Locked thresholds: <...>

## External oracle (independent of the loop that produced the model)
- Oracle: <name>  | mechanism: <how it's independent>  | how obtained: <...>

## Evidence
- Harness proof (planted-signal): <PASS/FAIL — metric, floor, noise band>
- External-oracle result: <metric=value, 95% CI=[..], n=..>  (metric: auroc/pearson/spearman)
- Closed-loop check: <in-sample-vs-oracle correlation; signature present? yes/no>
- Other moves run (baseline beat, threshold sweep, transfer, attribution): <...>

## VERDICT: < WORKING | NOT WORKING >

### If WORKING — name the boundaries (an honest WORKING always does):
- Input distributions covered: <...>
- Edge cases tested: <...>
- Why it works, causally: <...>
- **What is NOT covered:** <...>

### If NOT WORKING — name the cause (this is a result, not a failure):
- Which specific assumption failed: <...>
- What the evidence showed instead: <...>
- What would have to change for it to work: <...>

---
**Do not let downstream work depend on this claim until this card reads WORKING.**
