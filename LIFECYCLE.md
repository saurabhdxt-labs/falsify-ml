# The ML Project Lifecycle — "is this worth pursuing?"

> A model-agnostic framework for the whole life of an ML project. The question it answers is not
> "is this model claim trustworthy?" but the broader one practitioners actually face:
> **"given my idea, data, and current evidence, is this project worth pursuing?"**

Most ML failures happen **before** anyone runs a falsification test, and some happen after. A
project can pass every trust gate in [`PROTOCOL.md`](PROTOCOL.md) and still be a bad project —
because it solved the wrong problem, leaked the future into its features, trained on data that could
never support the claim, **isn't worth the cost to build**, or shipped with no way to notice when it
rots.

This document is the map. It names **ten stages**, the specific failure each one catches, the
checklist questions to answer, and the artifact to leave behind. Falsification — the deep,
attack-the-claim protocol — is **Stage 5**, one stage among ten, not the whole job.

Each stage emits a status — **PASS / FAIL / UNKNOWN** — and the statuses roll up into a single
top-level verdict on the [`feasibility_card.md`](templates/feasibility_card.md):
**PURSUE / DO NOT PURSUE / INSUFFICIENT EVIDENCE**. Three of the stages have **runnable tools**
(Stage 1 leakage, Stage 1.5 data-reality, Stage 2.5 value); the rest are fill-in checklists under
[`templates/`](templates/). Worked end-to-end examples across task types live under
[`examples/`](examples/).

**Works with just an idea, too.** You do not need data or code to start. The judgment stages
(0 framing, 2 baseline, 2.5 value) and the numbers-mode feasibility math (1.5) run on an idea alone
and can return DO NOT PURSUE — or INSUFFICIENT EVIDENCE with a clear "collect a pilot dataset next" —
before a single GPU hour is spent. The data-dependent stages (1, 1.5 CSV mode, 3, 5) stay UNKNOWN
until data exists, and the card says so honestly.

---

## Calibration first — this is not a reason to never ship

Applied maximally, a ten-stage gate could block every project behind infinite checklists. That is
the opposite failure. The same calibration as the falsification protocol applies to the whole
lifecycle:

- **Run every stage; size the rigor to the stakes.** A throwaway prototype answers each checklist
  in a sentence. A model going into a paper, a product, or a decision answers them with measurements
  and dated artifacts.
- **A stage you skip is a risk you are holding silently.** Skipping is allowed — *naming that you
  skipped it and why* is mandatory. An un-named skipped stage is exactly how the expensive failures
  happen.
- **Stages feed forward.** Each stage's artifact is an input to the next. The baseline you lock in
  Stage 2 is the bar Stage 5 must beat; the metric you justify in Stage 4 is the metric Stage 5
  pre-registers; the oracle you can reach in Stage 1 constrains the claim you can close in Stage 5.

---

## The ten stages

### Stage 0 — Frame the problem
**Catches:** building the wrong thing; using ML where a rule would do.
**Ask:**
- What decision does this model change? If nothing downstream changes, stop.
- What would "solved" look like with **no ML** — a rule, a lookup, a human? Write that down.
- Does a trivial heuristic already exist? Name it; it becomes your baseline floor.
- Is the target even the right target, or a convenient proxy for what you actually care about?

**Artifact:** [`templates/framing.md`](templates/framing.md)

### Stage 1 — Data contract + leakage
**Catches:** the "great model" that is really train/test contamination.
**Ask:**
- Is the label definition consistent across the data source? (If human-labeled, what is inter-rater
  agreement?)
- Is the train/test split **temporal or grouped**, not random row order? (Random splits leak when
  rows are correlated by entity or time.)
- Does any feature encode information unavailable at prediction time (future-info / target leakage)?
- Are there duplicate or near-duplicate rows spanning the split?

**Runnable tool:** `scripts/leakage_check.py --data <csv> --split-col <split>` mechanically detects
duplicate-rows-across-split, temporal overlap (`--time-col`), and group leakage (`--group-col`) as
hard fails, and flags a perfect-predictor feature as a SUSPECT for human review (never an auto-fail —
legitimate downstream-consequence features exist, e.g. `pregnant → gave_birth`).
**Artifact:** [`templates/data_contract.md`](templates/data_contract.md)

### Stage 1.5 — Data reality check
**Catches:** the project that cannot succeed because the **signal isn't in the data** — even with a
clean split, a sound metric, and a well-framed problem.
**Ask:**
- How many examples actually exist — enough to detect the effect size you need (see Stage 4 power)?
- What is the label-noise floor? If labels are X% wrong, your achievable precision is capped no
  matter how good the model is.
- What is the missingness rate, and is it missing-at-random or systematically?
- How stable is the target over time? If it drifts faster than you can learn it, no model holds.
- What is the irreducible uncertainty (Bayes-error ceiling) for this task? Are you trying to beat a
  ceiling that physics/labels make unreachable?

**Why separate from Stage 1:** leakage asks "is the data *clean*?"; this asks "is the signal even
*present*, in *enough* quantity, *above the noise*?" A dataset can be perfectly clean and still
unable to support the claim.

**Runnable tool:** `scripts/data_reality.py` — **numbers mode** (idea stage, no data):
`--n <N> --target-effect <r>` reports the minimum detectable correlation and whether your target is
reachable; `--label-error-rate <e> --required-precision <p>` reports the precision ceiling and a
DO-NOT-PURSUE if the requirement exceeds it. **CSV mode** (data exists): `--data <csv> --label-col y`
reports n, base rate, missingness, and (with `--gold-col`) label-noise from a re-labeled subset.
**Artifact:** [`templates/data_reality.md`](templates/data_reality.md)

### Stage 2 — Baseline before training
**Catches:** training a model, getting a number, then inventing the bar it clears.
**Ask:**
- What is the trivial/free baseline's measured performance (random, majority-class, last-value,
  a free public tool that already does this)?
- What is the **minimum marginal lift** over that baseline that would justify the model — committed
  *before* training, so it cannot be rationalized after?
- Is the target metric even achievable above the baseline given Stage 1.5's noise floor?

**Artifact:** [`templates/baseline.md`](templates/baseline.md)

### Stage 2.5 — Value / economics check
**Catches:** the project that is scientifically sound and economically pointless — clean data,
detectable signal, valid eval, and still not worth building (the "1% lift, $2M to deploy" case).
**Ask:**
- What is one unit of improvement worth, and how many units is the model realistically expected to
  add (use the conservative Stage-2 minimum lift, not the optimistic one)?
- What is the one-time build/deploy cost, and the ongoing per-period maintenance cost?
- Do the gains cover the cost — and does the build investment ever recover?

**Runnable tool:** `scripts/value_check.py --value-per-unit <v> --expected-lift <u> --deploy-cost <d>
--annual-maintenance <m>` → gross gain, annual net, payback period, and PASS (worth it) / FAIL
(gains never cover cost — DO NOT PURSUE on economics alone) / UNKNOWN (inputs missing).
**Artifact:** [`templates/value_case.md`](templates/value_case.md)

### Stage 3 — Training health
**Catches:** a model that converged to noise, or diverged silently.
**Ask:**
- Did loss/metric converge, or is the curve still moving / NaN / diverging?
- Is the per-sample loss distribution sane (no one cohort failing predictably)?
- Are there in-flight guards against NaN/Inf/gradient-spike aborts? (If you have project-level
  training guards, cross-link them here.)
- Does the train-vs-validation gap indicate overfitting?

**Artifact:** [`templates/training_health.md`](templates/training_health.md)

### Stage 4 — Eval design
**Catches:** accidental p-hacking; a metric that doesn't mean what you think.
**Ask:**
- Why **this** metric for **this** task? (AUROC for binary ranking quality, Pearson/RMSE for
  regression, rank-correlation/NDCG for ranking — justify the choice, don't default to it.)
- What effect size matters, and is your evaluation **n** large enough to detect it? (Power.)
- What confidence-interval method, and is the bootstrap N large enough for the CI to have
  converged?
- Are these chosen **before** looking at results, and locked (Stage 5 Gate 2 pre-registration)?

**Artifact:** [`templates/eval_design.md`](templates/eval_design.md)

### Stage 5 — Falsify the claim *(the deep dive)*
**Catches:** a claim that scores well in-sample while measuring nothing real.
This is the full falsification protocol — six gates and twelve moves — documented in
[`PROTOCOL.md`](PROTOCOL.md) and runnable via the `/falsify` skill
([`skills/falsify/SKILL.md`](skills/falsify/SKILL.md)):

1. State exactly one hypothesis.
2. Pre-register TRUE shape, FALSE shape, locked thresholds.
3. Name an independent external oracle (refuse closed loops).
4. Prove the harness works (planted-signal meta-falsification).
5. Run the closed-loop mutual-exclusivity diagnostic.
6. Record a WORKING (with coverage) / NOT WORKING (with cause) verdict.

**Artifact:** `falsify/<slug>/*` (written by the skill) + [`templates/verdict.md`](templates/verdict.md)

### Stage 6 — Deploy + monitor drift
**Catches:** the model that passed every gate and then rotted in production.
**Ask:**
- What does "drift" mean for this model concretely — feature-distribution shift? a drop in oracle
  correlation? a rise in a guardrail metric?
- What are the alert thresholds, and who/what watches them?
- What is the trigger to **retrain** vs. **roll back**?
- How often is the Stage-5 oracle test re-run in production, not just once at launch?

**Artifact:** [`templates/monitoring.md`](templates/monitoring.md)

### Stage 7 — Stopping rule
**Catches:** spinning in refinement cycles forever; never declaring done.
**Ask:**
- What pre-committed criteria mean "good enough to stop" (e.g. oracle ρ ≥ X **and** drift rate
  below Y)?
- What is the maximum iteration count or time budget before you escalate or abandon?
- For each WORKING verdict, which assumptions are most likely to become fragile over time, and what
  would re-open the hypothesis?

**Artifact:** [`templates/stopping.md`](templates/stopping.md)

---

## How the stages connect

```
0 Frame ─▶ 1 Data contract ─▶ 1.5 Data reality ─▶ 2 Baseline ─▶ 2.5 Value ─▶ 3 Train health
                                                                                   │
                                                                                   ▼
              7 Stopping ◀── 6 Deploy/monitor ◀── 5 Falsify ◀── 4 Eval design ◀────┘

  every stage → PASS / FAIL / UNKNOWN  ──rolls up──▶  feasibility_card.md
                                                       PURSUE / DO NOT PURSUE / INSUFFICIENT EVIDENCE
```

- Stage 0's named heuristic → Stage 2's baseline floor.
- Stage 1.5's noise ceiling → Stage 2's achievability check and Stage 4's power calc.
- Stage 2's minimum lift → Stage 2.5's `expected_lift` economics input.
- Stage 4's chosen metric → Stage 5's pre-registered metric → the diagnostics' `--metric` flag.
- Stage 5's oracle → Stage 6's production re-run cadence.
- Every stage's PASS/FAIL/UNKNOWN → the feasibility card's derived top verdict.

**Rollup rule (mechanical):** critical stages are **0, 1, 1.5, 2.5, 5**. Any critical FAIL →
**DO NOT PURSUE**; else any critical UNKNOWN → **INSUFFICIENT EVIDENCE**; all critical PASS →
**PURSUE**. PURSUE means "worth investing further," not "ship the model."

---

## One-line summary

**Ten stages, falsification is one of them, and the output is a go/no-go on whether the project is
worth pursuing. Run every stage; each emits PASS/FAIL/UNKNOWN; they roll up to PURSUE / DO NOT
PURSUE / INSUFFICIENT EVIDENCE. Most ML failures are upstream of the trust gate — frame the problem,
prove the data can support the claim, check the economics, lock the baseline and metric before
training, falsify the claim against an independent oracle, then watch for drift and know when to
stop. Works on a bare idea (judgment + numbers-mode feasibility) or on real data (the scripts run).**
