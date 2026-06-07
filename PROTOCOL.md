# The Falsification Protocol

> A discipline for trying to **kill** your ML project before it kills your time.
>
> Most ML validation asks "does it work?" and looks for evidence that it does.
> This protocol asks "**how would I know if it doesn't?**" and then tries hard to
> prove exactly that. A claim that survives a genuine attempt to refute it is worth
> something. A claim that was never seriously attacked is a rumor with a number
> attached.

Every rule below is here because its absence has cost real ML projects real time — weeks
to months spent building on a headline claim that was never measured against independent
evidence and turned out to be false. The point of the protocol is to make that class of
failure cost *you* a day instead of a quarter.

This document is the deep dive on **one stage** of an ML project: deciding whether to trust
a claim. It is Stage 5 of the broader lifecycle in [`LIFECYCLE.md`](LIFECYCLE.md) — the stages
before it (problem framing, data-contract + leakage, data reality, baseline, training health,
eval design) and after it (deployment, drift monitoring, stopping) catch failures that
falsification alone cannot. Read `LIFECYCLE.md` first for where this fits; read this for how to
run the trust stage itself.

---

## The core idea: a claim is a hypothesis until it is closed

Every load-bearing thing your project asserts — "the model works," "the benchmark is
valid," "this beats the baseline," "the detector detects the thing" — is a **hypothesis**,
not a fact, until it has been **closed** with a verdict against evidence that came from
*outside* the loop that produced it.

A hypothesis is *closed* when it has all six of:

1. a precise, one-sentence statement (one variable, one measurable outcome),
2. a predicted **TRUE shape** (what the numbers look like if it's real) — written **before** measuring,
3. a predicted **FALSE shape** (the counterfactual — what you'd see if it's wrong),
4. **independent external evidence** measured against both shapes,
5. a verdict of **WORKING** (with named coverage) or **NOT WORKING** (with a causal reason),
6. the verdict **written down**, dated, before any downstream work depends on it.

"Probably," "it seems to," "partially," "directionally," and "we'll measure that later"
are **not verdicts**. The default verdict, when evidence is ambiguous, is **NOT WORKING** —
the burden of proof is on the hypothesis to survive.

### One hypothesis at a time

The discipline is serial. When H1 is open, H2 does not exist yet. You do not chain
"if H1 then H2 follows" without closing H1 first — that chaining is exactly how a stack
of un-closed assumptions grows until the whole project is built on sand. Close the
blocker, *then* open the dependent claim with the blocker's verdict as input.

### NOT WORKING is a result, not a failure

A NOT WORKING verdict that names *which specific assumption failed and what the evidence
shows instead* is as valuable as a WORKING verdict — often more, because it stops you
spending another month on a dead direction. The failure mode is not "getting a NOT
WORKING." The failure mode is **never running the test that could have produced one.**

---

## The six steps, in order

### 1. State the hypothesis precisely

One sentence. One variable. One measurable outcome. It must be specific enough that it
*could*, in principle, come back red.

- ❌ "The model detects the thing." (un-testable — detects how well? measured against what?)
- ✅ *(classification)* "The model's per-instance score correlates with an independently-confirmed
  ground-truth label at Spearman ρ > 0.4 on instances neither the model nor its threshold ever saw
  during training."
- ✅ *(regression)* "The model's predicted value tracks the held-out true value at Pearson r > 0.6
  on a time period after everything it trained on, and beats a last-value-carried-forward baseline
  by ≥ 20% lower MAE."
- ✅ *(ranking)* "The model's ranking of held-out items agrees with the independently-measured
  preference order at rank correlation > 0.3, on queries it never saw."

The task and the metric change; the shape does not — one variable, one measurable outcome, a number
that could come back red. If you cannot write the sentence so a number could falsify it, you do not
have a hypothesis yet — you have a hope.

### 2. Predict the TRUE shape — in advance

Write the expected numbers, ranges, and relationships **before** you look at any result.
If you skip this, you will post-hoc rationalize whatever you see as success. The TRUE
shape goes in a file, dated, not in your head.

> Example: "If the model works, AUROC on held-out instances ≥ 0.75, AND it beats the obvious
> single-feature heuristic by ≥ 5 points, AND its top-decile precision ≥ 2× base rate."

### 3. Predict the FALSE shape — the counterfactual

What would you see if the hypothesis is wrong? If you cannot articulate this, the
hypothesis is **unfalsifiable and worthless** — discard it before wasting time measuring.

> Example: "If the model is just memorizing one dominant feature, then ablating (zeroing) that
> single feature collapses AUROC to ~0.5, and the model adds nothing over the obvious heuristic."

Every test must be able to go red. A test that cannot fail is decoration.

### 4. Gather evidence from OUTSIDE the closed loop

This is the step that gets skipped, and it is the most important one.

If the hypothesis is about model performance, the evidence **cannot come from the same
process that produced the model.** It cannot come from a test set drawn from the same
generator as the training set. It cannot come from a reporter that reads the model's own
output. It must come from:

- **an independent ground-truth source** (a different measurement mechanism, different
  sensors, different timing, a third-party label), or
- **real held-out data the model never saw** during training, benchmarking, *or*
  threshold-tuning, or
- **adversarial inputs you constructed specifically to break it.**

If no independent source exists for a genuinely novel claim, the closure bar goes **up,
not down**: multiple weak independent sources, empirical measurement on real held-out
data, adversarial construction. "We don't have an oracle, so we'll call it good" is the
single most expensive sentence in ML.

### 5. Return a verdict

**WORKING** or **NOT WORKING.** No middle ground.

- **WORKING** requires: which input distributions are covered, which edge cases are
  tested, *why* it works in causal terms, **and** an explicit list of what is **not**
  covered. Every honest WORKING names its own boundaries. "Tests pass" is not WORKING —
  tests pass inside closed loops too.
- **NOT WORKING** requires: which specific assumption failed, what the evidence shows
  instead, and what would have to change for the hypothesis to work.

### 6. Write it down, then move on

One verdict per entry, dated, in a versioned file. Then — and only then — open the next
hypothesis. Do not re-litigate a closed verdict without new evidence. Do not carry an
open hypothesis forward as if it were closed.

---

## What actually worked: twelve falsification moves that killed false claims

These are not theoretical. Each one caught a real false claim or a real failure mode in
practice. They are phrased generically so you can apply them to any ML project.

### 1. Holdout-honesty test (catch in-sample self-dealing)
Refit the model many times, each time holding out a small random slice of the labeled
data, and score that slice with the *same* metric and threshold you'd use in production.
Report the distribution across seeds. If the held-out number is far below the full-data
number, your headline was self-dealing. *Cheap; run it before trusting any train metric.*

### 2. External-oracle correlation (the decoupling test)
Get an independent measurement of the same ground truth and correlate it with your model's
score on the same cases. Pre-commit a minimum (e.g., ρ > 0.2 with a CI lower bound above
zero). **The diagnostic signature of a closed loop:** high in-sample fit paired with
near-zero external correlation. If you see that pattern, your in-sample numbers are
measuring your own generator, not reality.

### 3. The closed-loop mutual-exclusivity sweep (the crown jewel)
Measure *both* in-sample fit and external-oracle correlation across many model variants,
and plot one against the other. If the variants that fit best in-sample are exactly the
ones with the *lowest* external correlation — and vice versa — you have found closed-loop
measurement directly. The architecture is learning your data generator, not the signal.
This is stronger evidence than any single test. The pathological case is a *perfect*
anti-correlation: the variant that fits best in-sample is dead-last on the oracle, and the
worst in-sample variant has the highest oracle correlation — a textbook signature that the
architecture is fitting the generator, not the signal.

### 4. Planted-signal meta-falsification (test your harness before you trust it)
Before you believe any NOT WORKING verdict, prove your pipeline can find a signal that is
*obviously* there. Inject a synthetic feature where positives sit 10 standard deviations
away from negatives, run it through your *entire* pipeline unchanged, and confirm near-perfect
detection. Then inject pure noise and confirm rejection. If the harness can't detect a
10σ signal or can't reject noise, **the harness is broken and every other result is
meaningless.** Run this first. *(This is the test that proves your falsification machinery
itself works — the most-skipped and most-important meta-step.)*

### 5. Oracle ground-truth audit (is your "truth" actually true?)
Don't assume your independent oracle is perfect. Audit it: does it show temporal
consistency (lag-1 autocorrelation)? does it light up on cases you *know* are positive?
does it stay quiet on cases you *know* are negative? If the oracle has blind spots,
quantify them and propagate that uncertainty into every claim that leans on it.

### 6. Threshold-sensitivity sweep (is the verdict brittle?)
Re-run the verdict under a stricter and a looser threshold. If a NOT WORKING flips to
WORKING the moment you soften the bar, the result is brittle and threshold-dependent. If
it stays NOT WORKING across the whole range, the problem is structural — not a bar that
was set too high. This pre-empts the "but if you just relaxed the threshold..." argument.

### 7. Cross-domain transfer (does it generalize or memorize?)
Take the trained model, *without retraining*, and apply it to a different domain where you
also know the ground truth. If it was learning a real causal pattern, it transfers. If it
fires on everything (including known-quiet cases in the new domain), it's not a detector —
it's a "distance from its training distribution" counter wearing a detector's name.

### 8. Beat the free/trivial baseline (or you have no product)
Compare against: random ordering, the dumbest domain-appropriate heuristic, and — critically —
any **free public data or tool** that already does the job. If a user gets equal or better
results from a free source, your model's marginal value is zero regardless of its internal
metrics. This single comparison has killed otherwise-impressive product framings: if a free public
source matches or beats the trained model, the model adds nothing a buyer would pay for.

### 9. Corpus selection-bias audit (is your test set representative?)
Check that no single class/region/segment dominates (< 50% share), that the data isn't
clustered on one date, and that positive and negative groups are matched on confounds
(volume, exposure, time). A model can look great because the test set was quietly stacked.

### 10. Statistical-methodology audit (is the CI honest?)
Use non-parametric percentile bootstrap with a fixed seed for small samples. Check that
your bootstrap N is large enough that the CI width has converged. Don't report a tight CI
that's an artifact of too few resamples, and don't claim significance an honest CI wouldn't
support.

### 11. Component / fallback attribution (what's *actually* doing the work?)
If your system has multiple paths ("use the neural model, else fall back to a heuristic"),
**instrument it to record which path fired for every positive prediction.** A headline like
"the neural model detects X" is a masquerade if the fallback path produced the overwhelming
majority of the hits and the named component produced almost none. You can only catch this by tagging contributions —
overall metrics will happily hide it. This is one of the most expensive failures in practice:
the named component contributes almost nothing, a fallback does the work, and nobody measures
the component alone because the pipeline's overall metric looks fine.

### 12. Pre-committed, date-locked thresholds (make goalpost-moving visible)
Write every threshold into a dated, version-controlled file **before** the experiment runs,
and cite that file by path+date whenever you apply the threshold. Any later change requires
a *new* dated file — which shows up in git history. This doesn't prevent you from changing
your mind; it makes post-hoc threshold-softening **visible to an auditor (including
future-you).**

---

## What didn't work: eight gaps that let false claims survive

Each of these let a wrong claim live — sometimes for weeks. For each, the gate that would
have caught it on day one.

| # | Failure mode | How it hides | The day-one gate that catches it |
|---|---|---|---|
| 1 | **Closed-loop benchmark** — train and test drawn from the same generator | Internal metrics look great because they measure consistency with the generator, not reality | "No claim is promoted until it's tested against an *independent* oracle." Run the oracle test on day 1, not day 60. |
| 2 | **Synthetic/real distribution mismatch** — synthetic positives live in a range real positives never reach | Model learns the synthetic range; fails silently on real data outside it | Measure feature distributions of synthetic vs real positives side-by-side (KS statistic) *before* training. Red if the ranges don't overlap. |
| 3 | **Post-hoc threshold optimization** — soften the bar after seeing a marginal result | The softer number becomes the headline; the move is invisible | Date-lock thresholds in version control before running (move #12). |
| 4 | **Structurally unachievable baseline** — a recall@K target that's mathematically impossible given the data | Every model "fails," so you blame the models when the bar was wrong | Compute the theoretical max of your metric on the corpus *before* committing the threshold. |
| 5 | **Cross-season / cross-time confound** — "quiet" controls drift over time and start tripping the detector | The detector looks like it fires on events; really it fires on time-drift | Score this-period's controls against a *different* period's baseline; report the leakage rate. |
| 6 | **Non-comparable scoring across variants** — different models scored on different metrics, compared as if uniform | "All 9 failed" hides that 3 were measured differently | Force a common metric, or label every exception explicitly in the results table. |
| 7 | **Hidden shared-oracle dependence** — "three independent tests" that all use the same ground-truth source | Claimed independence inflates confidence | List the oracle for every test; never claim independence across tests that share one. |
| 8 | **Underpowered external sample** — a strong ρ computed on a handful of cases because the oracle only joined a few | A big correlation on a tiny n reads as strong evidence | Pre-commit the minimum n for a credible external claim; downgrade confidence when oracle coverage is below it. |

---

## Calibration: this is not a reason to never ship

Applied maximally, this protocol could block every step behind an infinite "but is *that*
closed?" regress. That's the opposite failure. Calibrate:

- **Apply the full loop to LOAD-BEARING claims only** — the ones a downstream decision,
  pitch, paper, or release depends on. "This function multiplies correctly" is not
  load-bearing (a unit test covers it). "This model detects the real thing" is.
- **Trust closed verdicts downstream.** Once a hypothesis is closed WORKING with external
  evidence, build on it without re-closing — unless new evidence contradicts it.
- **"Open but risk-acknowledged" is a valid state** for non-urgent work, *if you say so
  out loud* and the current step doesn't claim the open hypothesis is true.
- **Small moves don't open hypotheses.** Typos, refactors, docstrings — proceed. The loop
  fires for significant claims: promotions, "X detects Y" headlines, benchmark-beat claims,
  anything buyer/paper/release-facing.
- **Close with the best available evidence and label its strength honestly.** "Closed
  WORKING, weak-evidence tier, one independent source, to be strengthened" beats leaving
  it open *and* beats a false-confident WORKING. The rule is not "perfect closure or no
  movement" — it's "**no claim is carried forward as an assumption; every load-bearing
  claim gets a verdict at whatever confidence the evidence supports, honestly labeled.**"

---

## One-line summary

**Open one hypothesis. Write its TRUE shape and FALSE shape before measuring. Gather
evidence from outside the loop. Prove your harness can find a planted signal and reject
noise. Return WORKING (with coverage) or NOT WORKING (with cause). Write it down. Move on.
Never chain without closing.**

---

## Origin

This protocol was distilled from real ML-validation failures — the kind where a project carries an
un-tested headline claim for weeks or months, builds on top of it, and only discovers it was false
the first time it's measured against independent evidence. These failure modes are common and
generic: a benchmark that shares a generator with training, a "detector" whose work is actually done
by a fallback path nobody measured alone, a strong correlation computed on a sample too small to mean
anything, a threshold quietly softened after the result was seen. The rules and moves above each
exist because one of these cost real time in practice. They are stated generically because the
failure modes are generic; the point is that the discipline was paid for, not invented.

---

*This protocol is methodology only. It contains no proprietary model, data, or result —
it is the generalized discipline, not the project that paid for it.*
