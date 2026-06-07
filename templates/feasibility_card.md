# Feasibility Card — <project/claim name>

> The top-level deliverable of the lifecycle: **is this ML project worth pursuing?**
> Each stage emits PASS / FAIL / UNKNOWN; the verdict is *derived* from the table, not free-typed.
> See ../LIFECYCLE.md for what each stage checks.

**Date:** <YYYY-MM-DD>  **Mode:** < idea-only | data+code >

## Stage status table

| # | Stage | Status | Reason / evidence |
|---|-------|--------|-------------------|
| 0 | Frame the problem | <PASS/FAIL/UNKNOWN> | <...> |
| 1 | Data contract + leakage | <PASS/FAIL/UNKNOWN> | <leakage_check.py output, or "no data yet"> |
| 1.5 | Data reality | <PASS/FAIL/UNKNOWN> | <data_reality.py output> |
| 2 | Baseline before training | <PASS/FAIL/UNKNOWN> | <...> |
| 2.5 | Value / economics | <PASS/FAIL/UNKNOWN> | <value_check.py output> |
| 3 | Training health | <PASS/FAIL/UNKNOWN> | <...> |
| 4 | Eval design | <PASS/FAIL/UNKNOWN> | <...> |
| 5 | Falsify the claim | <PASS/FAIL/UNKNOWN> | <verdict.md / closed_loop_check.py output> |
| 6 | Deploy + monitor | <PASS/FAIL/UNKNOWN> | <...> |
| 7 | Stopping rule | <PASS/FAIL/UNKNOWN> | <...> |

**Critical stages** (a FAIL here is decisive): 0, 1, 1.5, 2.5, 5. The others can be UNKNOWN at the
idea stage without sinking the project — they get closed once data/training/deploy exist.

## Derivation rule (apply mechanically)
1. **DO NOT PURSUE** — if ANY critical stage is **FAIL**. Name which one and why.
2. **INSUFFICIENT EVIDENCE** — if no critical FAIL, but any critical stage is **UNKNOWN**
   (typical idea-stage outcome: framing/value PASS, but data-dependent 1/1.5/5 not yet closable).
3. **PURSUE** — only if ALL critical stages are **PASS**.

## VERDICT: < PURSUE | DO NOT PURSUE | INSUFFICIENT EVIDENCE >

**Deriving reason:** <e.g. "DO NOT PURSUE: Stage 1.5 FAIL — required precision 0.95 exceeds the
0.90 label-noise ceiling, unreachable regardless of model." OR "INSUFFICIENT EVIDENCE: Stages 1,
1.5, 5 UNKNOWN — no data collected yet; framing, baseline, and economics all PASS, so collecting a
pilot dataset is the next step.">

**Open stages to close next:** <list the UNKNOWN critical stages and what would close each>

---
*PURSUE means "worth investing further," not "ship the model." The model still has to clear Stage 5
falsification on real data before any claim is trusted.*
