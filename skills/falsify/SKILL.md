---
name: falsify
description: "Try to KILL any ML idea or project before it kills your time. Fires before you trust any model, benchmark, detector, classifier, predictor, or learning-based claim — and before you build downstream on top of one. Works for any ML project (classification, regression, ranking, anomaly detection, recommendation, time-series prediction — any task with a claim and a metric). Runs the falsification protocol as a gate: state one hypothesis, pre-register its TRUE and FALSE shapes with locked thresholds, name an INDEPENDENT external oracle (refuses closed-loop evidence), prove the harness can detect a planted 10-sigma signal and reject noise, run the closed-loop mutual-exclusivity diagnostic, and record a WORKING (with coverage) or NOT WORKING (with cause) verdict. Refuses \"probably\" / \"it seems to\" / \"tests pass\" as verdicts. Invoke when proposing or evaluating any ML claim, or via /falsify."
disable-model-invocation: false
allowed-tools: Bash Read Grep Glob Write Edit
---

# /falsify — try to kill this ML claim before you trust it

You are helping the user evaluate an ML claim — a model, a benchmark, a detector, a
predictor, a "this beats the baseline." It can be any ML task: classification, regression,
ranking, anomaly detection, recommendation, time-series prediction, or anything else with a
claim and a metric. STOP before agreeing it works. Your job in this skill is **not** to help
it pass. Your job is to **try as hard as you can to prove it is wrong**, and to let it
survive only if it genuinely does.

A claim that was never seriously attacked is a rumor with a number attached. This skill is
the serious attack.

**Finding the repo files.** This skill may be installed as a symlink into `~/.claude/skills/falsify`,
so plain relative links can be unreliable. The scripts are always in `scripts/` **next to this
SKILL.md**. The wider repo files (`LIFECYCLE.md`, `PROTOCOL.md`, `templates/`, `examples/`) live at
the **repo root, two directories up from this file** — i.e. `<dir of SKILL.md>/../../`. To get the
concrete path, resolve the SKILL.md location and go up two levels, or run
`python3 "$(dirname SKILL.md)/scripts/.." ` — simplest: the repo root is the parent of the `skills/`
directory that contains this skill. When you cite these files to the user, resolve and show the real
path.

**Where this sits in the ML lifecycle.** Falsification is **Stage 5** of a ten-stage ML project
lifecycle (`LIFECYCLE.md` at the repo root). Most ML failures happen *upstream* of this
gate: a wrong problem (Stage 0), a leaked split (Stage 1), data that can't support the claim
(Stage 1.5), no baseline (Stage 2), economics that don't work (Stage 2.5), an unhealthy training run
(Stage 3), a mis-chosen metric (Stage 4). And some happen *downstream*: silent drift after deploy
(Stage 6), never knowing when to stop (Stage 7). This skill runs the trust gate well — but if the
user hasn't walked the earlier stages, **say so and walk the whole lifecycle (next section)**,
because a claim can pass every gate here and still rest on a broken foundation. The templates for
every stage are in `templates/` at the repo root.

---

## Running the whole lifecycle — "is this worth pursuing?"

### First — figure out what you're falsifying (especially when invoked with no arguments)

If the user gave a claim or idea in the invocation, use it. **If `/falsify` was invoked with no
arguments, do NOT invent a claim and do NOT silently reuse a previous one.** Instead, look at the
current working directory and branch:

1. **Detect an already-started project.** Check the CWD (and one level down) for ML-project markers:
   - a prior falsify run: a `falsify/<slug>/` directory with a `hypothesis.md` / `feasibility_card.md`
     → offer to **resume/refresh** that run (name the slug);
   - data: `*.csv`, `*.parquet`, `data/`, `datasets/`;
   - model/training code: `train*.py`, `model*.py`, `*.ipynb`, or ML deps in `requirements.txt` /
     `pyproject.toml` / `environment.yml` (sklearn, torch, tensorflow, xgboost, lightgbm, …).
   Use a quick read-only sweep (`ls`, `find -maxdepth 2`, `grep` the deps file) — do not run anything
   heavy.

2. **If markers are found**, say what you found and ask the user to confirm the claim to attack —
   e.g. *"This looks like an ML project (found `train.py`, `data/train.csv`). What's the one claim you
   want me to try to kill — e.g. 'model X predicts Y at metric ≥ Z on held-out data'?"* Then run the
   **data + code** branch on it.

3. **If no markers are found** (empty/non-ML folder), ask the **idea question** directly:
   *"Which ML idea do you want me to check? One sentence — 'predict/detect/classify X from Y' — and
   I'll try to kill it before you build it."* Then run the **idea-only** branch.

Never proceed to the gates without a claim in hand. A missing claim is a STOP, not a guess.

---

The user may arrive with **a bare idea** or with **data + code**. Either way, the goal is a single
`templates/feasibility_card.md` verdict: **PURSUE / DO NOT PURSUE /
INSUFFICIENT EVIDENCE**. Walk the stages in order; each emits **PASS / FAIL / UNKNOWN**; roll them up
by the card's rule (any critical FAIL → DO NOT PURSUE; else any critical UNKNOWN → INSUFFICIENT
EVIDENCE; all critical PASS → PURSUE). Critical stages: 0, 1, 1.5, 2.5, 5.

**If the user has only an idea (no data, no code):**
- Walk **Stage 0 (framing)**, **Stage 2 (baseline)**, **Stage 2.5 (value)** as a guided interview
  using the templates — these need judgment, not data, and an idea can already FAIL here ("ML isn't
  needed," "a free tool already does this," "economics never work").
- Run **Stage 1.5 in numbers mode** for a feasibility estimate:
  `data_reality.py --n <best-guess N> --target-effect <r you'd need>` and
  `--label-error-rate <e> --required-precision <p>`. This can return DO NOT PURSUE before any data
  exists (e.g. required precision above the label-noise ceiling).
- **Data scoping is interactive, not automated.** If the user has no data, help them reason about
  what data and sources would be needed and whether any plausibly exist — record it in `framing.md`.
  **Do not pretend to fetch datasets or engineer features**; the skill never does that automatically
  (those are research/modeling tasks, and feature-engineering is "help the claim pass," the opposite
  of this skill's job). Surface them as "here's what you'd need," a finding, not an action.
- The data-dependent stages (1, 1.5 CSV mode, 3, 5) stay **UNKNOWN**; the card's honest verdict for a
  promising idea with no data yet is **INSUFFICIENT EVIDENCE — collect a pilot dataset next**.

**If the user has data + code:**
- Same walk, but the runnable stages execute on their data:
  **Stage 1** → `leakage_check.py --data <csv> --split-col <split> [--time-col --group-col --label-col]`;
  **Stage 1.5** → `data_reality.py --data <csv> --label-col <y> [--gold-col <gold>]`;
  **Stage 2.5** → `value_check.py` with their economics;
  **Stage 5** → the falsification gates below (`planted_signal.py`, `closed_loop_check.py`).
- Stage 3 (training health) is read from their training curve via the checklist; Stages 4/6/7 are
  judgment checklists. Fill the card from the measured statuses.

Either way: **PURSUE means "worth investing further," not "ship the model."** A PURSUE still has to
clear Stage 5 falsification on real data before any claim is trusted.

**Task shapes and metrics.** This gate is not binary-classification-only. The diagnostics take a
`--metric` flag: `auroc` (binary classification, default), `pearson` (regression), `spearman`
(ranking / monotonic). Pick the metric your Stage-4 eval design justified. Worked end-to-end
examples for classification and regression live in `examples/` at the repo root.

Read `PROTOCOL.md` in this repo for the full reasoning behind this stage. This file is the runnable
gate.

---

## The contract

You will walk the user through **six gates, in order**. You do not skip a gate because the
project "is small" or "is just a prototype" — prototypes become the thing that ships, so
treat day one as production. If the user refuses a gate, you **stop** and tell them which
gate they refused and what it would have caught. You do not write a WORKING verdict on a
refused gate.

The two automated diagnostics (`scripts/closed_loop_check.py`, `scripts/planted_signal.py`)
are run when their gate is reached, on the user's *own* data. Everything else is you
walking the protocol with them and writing the artifacts.

**Running the scripts.** They are pure Python standard library — no numpy/scipy/pandas — and
run on any Python 3.8+. Invoke them with `python3` (not `!python`); if your default `python3`
is missing a feature, use a fuller interpreter such as `python3.11`. Paths resolve relative to
the falsify-ml repo root by default, so run from there. To run from anywhere else, point
`FALSIFY_SKILL_DIR` at the skill folder:

```
export FALSIFY_SKILL_DIR=/path/to/falsify-ml/skills/falsify   # optional; defaults to skills/falsify
python3 "${FALSIFY_SKILL_DIR:-skills/falsify}/scripts/planted_signal.py" --self-test
```

`export` on its own line, then run — **not** an inline `FALSIFY_SKILL_DIR=... python3 "${FALSIFY_SKILL_DIR:-...}/..."`
prefix, because the shell expands `${FALSIFY_SKILL_DIR:-...}` before the inline assignment takes
effect, so the prefix is ignored. All script examples below use the
`"${FALSIFY_SKILL_DIR:-skills/falsify}/scripts/..."` form so they work from the repo root by default
and from anywhere once `FALSIFY_SKILL_DIR` is exported.

**The slug.** Pick one kebab-case slug for the hypothesis (e.g. `churn-oracle-rho`) and reuse it
across every gate so all artifacts land together under `falsify/<slug>/`.

---

## Gate 1 — State exactly one hypothesis

Make the user write **one sentence**: one variable, one measurable outcome, specific enough
that a number could falsify it.

Refuse vague forms. "The model detects fraud" is not a hypothesis. Push until it reads like:
"The model's per-transaction score correlates with independently-confirmed chargeback labels
at ρ > 0.4 on transactions it never saw in training or threshold-tuning."

If they have several claims, pick the **single most load-bearing one** (the one a pitch,
paper, release, or downstream step depends on) and park the rest. One hypothesis at a time.

**Write it** to `falsify/<slug>/hypothesis.md`.

## Gate 2 — Pre-register TRUE shape, FALSE shape, and locked thresholds

Before any result is looked at, make the user write:

- **TRUE shape:** the numbers/ranges/relationships expected *if the claim is real*.
- **FALSE shape:** the counterfactual — what the numbers look like *if it's wrong*. If they
  cannot write a FALSE shape, the hypothesis is unfalsifiable; **stop** and tell them so.
- **Thresholds:** every pass/fail bar, with its value.

Then **lock them**: write the pre-registration to a dated file and record it so any later
change is visible.

```
python3 "${FALSIFY_SKILL_DIR:-skills/falsify}/scripts/prereg_lock.py" --slug "<slug>" \
    --true-shape "<...>" --false-shape "<...>" --thresholds "<k=v;k=v>"
```

For long, multi-line shapes that are awkward to quote on the command line, write them to files
and pass `--true-shape-file`, `--false-shape-file`, `--thresholds-file` instead (inline and
`-file` forms for the same field are mutually exclusive). The script writes
`falsify/<slug>/prereg_<DATE>.md` (override the directory with `--out-dir`), prints a SHA-256 of
the locked content, and **refuses to overwrite an existing file for the same date** — a changed
threshold must become a *new* dated file. The date + hash lock the content now; once the file lives in a committed repo, git history
also makes any later change visible to an auditor.

(If `prereg_lock.py` is not present in this build, write the pre-registration to
`falsify/<slug>/prereg_<DATE>.md` by hand and tell the user that any change requires a new
dated file — the date IS the lock.)

The rule you enforce out loud: **a threshold cannot move after the result is seen without a
new dated file.** Goalpost-moving must be visible.

## Gate 3 — Name an INDEPENDENT external oracle (refuse closed loops)

Ask: *what evidence will close this hypothesis, and where does it come from?*

You **refuse** evidence that comes from inside the loop that produced the model:

- ❌ a test set drawn from the same generator as the training set
- ❌ a reporter that reads the model's own output back to you
- ❌ "the benchmark passes" when the benchmark shares a generator with training

You **require** at least one of:

- ✅ an independent ground-truth source (different mechanism, sensors, timing, or third-party label)
- ✅ real held-out data the model never saw in training **or** threshold-tuning
- ✅ adversarial inputs constructed specifically to break the claim

If no independent oracle exists for a genuinely novel claim, the bar goes **up**: demand
multiple weak independent sources, real held-out data, and adversarial construction. "We
don't have an oracle, so we'll call it good" is **refused** — name the oracle or the project
does not close this claim.

Record the oracle (name, how to obtain it, why it is independent) in `falsify/<slug>/oracle.md`.

## Gate 4 — Prove the harness works (planted-signal meta-falsification)

**Before** trusting any verdict — WORKING or NOT WORKING — prove a signal that is *obviously*
there can be found and obvious noise can be rejected. There are two distinct claims here; do not
let one stand in for the other.

**First, pick the metric for the task** — the diagnostic is not classification-only. Pass `--metric`:
`auroc` for binary classification, `pearson` for regression (continuous targets), `spearman` for
ranking / monotonic relationships. Use the metric your Stage-4 eval design justified. Everything
below works identically for all three; the examples just pick one. (`--metric` defaults to `auroc`
because binary classification is the most common case, but it is a default, not a privileged path —
regression and ranking are first-class.)

**4a — The stats ruler is straight (self-test).** This proves the diagnostic *math* (the chosen
metric's computation) works. It does **not** prove the user's ML pipeline works.

```
# classification:  python3 ".../scripts/planted_signal.py" --self-test --metric auroc
# regression:      python3 ".../scripts/planted_signal.py" --self-test --metric pearson
# ranking:         python3 ".../scripts/planted_signal.py" --self-test --metric spearman
python3 "${FALSIFY_SKILL_DIR:-skills/falsify}/scripts/planted_signal.py" --self-test --metric <metric>
```

It injects an obvious planted signal and confirms the metric is near-perfect (AUROC→1.0, or
correlation→1.0), then injects pure noise and confirms the metric collapses to its no-skill floor
(AUROC→0.5, or correlation→0). If this fails, the diagnostic itself is broken and every later number
is meaningless — **STOP and fix the plumbing first.**

**4b — The user's pipeline separates the cases it scored.** Run the metric on the user's *own* scored
output — a CSV with a score column and a target column (binary 0/1 for `auroc`; continuous for
`pearson`/`spearman` — continuous targets are accepted, not rejected):

```
python3 "${FALSIFY_SKILL_DIR:-skills/falsify}/scripts/planted_signal.py" \
    --scores <path.csv> --score-col <score> --labels-col <target> --metric <metric>
```

This proves the relationship **on these particular outputs only**. It does *not* prove a strong
feature survives the user's full train→infer path.

The self-test (4a) has tunable defaults if you ever need them: `--n` (rows, default 2000),
`--sigma` (separation, default 10), `--seed`, `--metric` (default `auroc`), `--auroc-floor` (signal
floor — default 0.99 for auroc, 0.8 for correlation metrics; must lie in the metric's valid range:
[0,1] for auroc, [-1,1] for pearson/spearman), and `--noise-band` (default `0.40,0.60` for auroc,
`-0.1,0.1` for correlations). Out-of-range or inverted values are rejected loudly rather than
producing a vacuous PASS/FAIL. The defaults are calibrated; change them only with a reason.

**4c — The strongest form (no script can do this for you): true upstream injection.** Add a
synthetic feature where known-positives sit ~10σ from known-negatives, then re-run the user's
**entire pipeline unchanged** (training and inference), score the result, and feed *that* output
to 4b. If the planted signal does not come out near-perfectly separated, the pipeline is losing
signal somewhere and no in-sample number can be trusted. Walk this by hand with the user when
their pipeline supports injection.

- Harness **detects the planted signal AND rejects noise** → the machinery is sound; proceed.
  Any NOT WORKING you reach later is about the *claim*, not broken plumbing.
- Harness **cannot detect a 10σ signal or cannot reject noise** → **STOP.** Fix the plumbing first.

If `planted_signal.py` is not present in this build, do 4a by hand: construct an obvious signal in
your task's terms (two well-separated groups for classification, or a strong linear/monotone relation
for regression/ranking), compute your chosen metric, confirm it is near-perfect; then score pure
noise and confirm the metric collapses to its no-skill floor. Record either way in
`falsify/<slug>/meta_falsification.md`.

## Gate 5 — Run the closed-loop mutual-exclusivity diagnostic

This is the move that catches the most expensive failure: a model that scores beautifully
in-sample while measuring nothing real.

Run the diagnostic on the user's in-sample score and their oracle score for the same cases.
**Input contract:** two CSVs, each with a named score column and a shared ID column. The two are
**joined on the ID** — never on row order, because independent oracle data rarely arrives in the
same order. Unmatched or duplicate IDs are a loud error, not a silent mis-pairing.

```
python3 "${FALSIFY_SKILL_DIR:-skills/falsify}/scripts/closed_loop_check.py" \
    --in-sample <in.csv> --in-col <score> --oracle <oracle.csv> --oracle-col <score> \
    --id-col <id> [--metric spearman|pearson]
```

(Only if you are certain both files are already row-aligned may you pass `--assume-aligned`
instead of `--id-col`; it warns and pairs by position. If the two files use **different** id column
names, pass `--in-id-col` and `--oracle-id-col` instead of the shared `--id-col`. `--metric`
defaults to `spearman` — monotonic/ranking agreement; use `pearson` for a linear/regression
relationship.)

It reports the external-oracle correlation (Spearman ρ or Pearson r with a bootstrap CI) on the
joined cases,
flags small samples (it rejects n below `--min-n`, default 20, and prints an UNDERPOWERED warning
below `--warn-n`, default 30), and — if the user passes `--variants <csv>` with
`in_sample_fit,oracle_corr` columns —
whether the variants that fit best in-sample are the ones with the *lowest* oracle correlation.
**That anti-correlation is the signature of a closed loop:** the model is learning the generator,
not the signal.

If `closed_loop_check.py` is not present in this build, compute Spearman ρ between the joined
in-sample and oracle scores by hand, bootstrap a 95% CI, and apply the same interpretation below.

Interpret out loud:
- High in-sample fit **and** near-zero oracle ρ → closed loop. The in-sample number is not
  trustworthy. Lean toward NOT WORKING.
- In-sample fit **and** oracle ρ both clear their pre-registered bars (CI lower bound > 0) →
  the claim has external support. Eligible for WORKING.

Also walk these by hand where applicable (they have no script but are part of the gate):
component/fallback attribution (what path actually produced the positives?), beat-the-free-baseline,
threshold-sensitivity sweep, cross-domain transfer. See `PROTOCOL.md` moves 6–11.

Record everything in `falsify/<slug>/evidence.md`.

## Gate 6 — Record a verdict

**WORKING** or **NOT WORKING.** No "probably," "partially," "directionally," or "tests pass."
If the evidence is ambiguous, the verdict is **NOT WORKING** — the burden is on the claim.

- **WORKING** must name: which input distributions are covered, which edge cases are tested,
  *why* it works causally, and **explicitly what is NOT covered.**
- **NOT WORKING** must name: which assumption failed, what the evidence showed instead, and
  what would have to change.

Write the verdict card to `falsify/<slug>/verdict.md`, dated. Then stop — do not let
downstream work depend on this claim until the card says WORKING.

---

## What this skill refuses

- It does not let "the tests pass" stand in for external evidence (tests pass inside closed loops too).
- It does not accept "probably" / "it seems to" / "we'll measure that later" as a verdict.
- It does not let the user skip a gate because the idea is small or a prototype.
- It does not write WORKING on a refused gate — it stops and names the gap.

## When it fires

- The user proposes an ML idea, model, detector, classifier, or predictor (any ML task).
- The user reports a benchmark or "it beats the baseline" result.
- The user is about to build downstream on top of an un-closed model claim.
- It does **not** fire on infrastructure work (logging, refactoring, plumbing, docs).

---

*This skill is methodology only. It contains no proprietary model, data, or result. The
diagnostics run on the user's own project; nothing about the project that originated this
discipline is embedded here.*
