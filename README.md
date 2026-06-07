# falsify — *is this ML project worth pursuing?*

A model-agnostic framework for deciding whether an ML project is worth your time — **before** you
burn weeks and GPU hours on it, and before you trust any claim it produces. It walks ten lifecycle
stages and returns a single verdict: **PURSUE / DO NOT PURSUE / INSUFFICIENT EVIDENCE**.

Most ML tooling helps you *build*. Almost nothing helps you **kill a bad idea before you build it**,
or catch a model that scores beautifully while measuring nothing real. That's the gap this fills: it
asks "how would I know if this *doesn't* work?" and then tries hard to prove exactly that.

The deepest stage is *falsification* — trying as hard as possible to **kill** a model claim rather
than confirm it — but that is one stage of ten, not the whole job. Most ML projects fail upstream
(wrong problem, leaked split, data that can't support the claim, no baseline, bad economics) or
downstream (silent drift, never knowing when to stop). This framework covers all of it.

Distilled from real ML-validation failures; pure Python standard library, **zero third-party
dependencies**, runs on any Python 3.8+.

**Scope:** this is for **ML claims** — models, detectors, classifiers, forecasters, rankers that
have *data, labels, and a metric*. It is **not** an LLM/agent/generative-quality evaluator (those
need different machinery — eval-set design, judge calibration, grounding tests). If your "AI" is a
classifier with labels and a held-out metric, it fits; if it's a chatbot or an agent, it doesn't.

---

## Install

```
git clone https://github.com/saurabhdxt-labs/falsify-ml.git
cd falsify-ml
./install.sh
```

`install.sh` symlinks two things (so future `git pull`s are picked up live — no re-install):

| Symlink | What it enables |
|---|---|
| `~/.claude/skills/falsify` → `skills/falsify/` | the **`/falsify` Claude Code skill** (the guided walkthrough) |
| `~/.local/bin/falsify` → `bin/falsify` | the **`falsify` CLI** (the standalone diagnostics, no Claude) |

If `~/.local/bin` isn't on your `PATH`, the installer prints the line to add (it won't edit your
shell rc for you). `./uninstall.sh` removes both symlinks (and never deletes anything it didn't
create).

You don't have to install to try it — the scripts run directly:
`python3 skills/falsify/scripts/data_reality.py --n 150 --target-effect 0.3`. The `/falsify` skill
requires [Claude Code](https://claude.com/claude-code); the CLI does not.

---

## Does it work without Claude?

**The diagnostics do; the guided walkthrough needs Claude.** Two front doors, same repo:

| Part | Needs Claude? | What you get |
|---|---|---|
| **`falsify` CLI** | ❌ No | the six pure-Python diagnostics, run in any terminal |
| **`/falsify` skill** | ✅ Yes | the interactive 10-stage walkthrough + judgment stages + the filled-in PURSUE/DON'T feasibility card |

So the math, leakage checks, and feasibility estimates are a genuine standalone tool. Claude adds the
*"walk me through it and decide"* experience.

---

## The standalone CLI (no Claude)

```
falsify --help          # list subcommands
falsify --where         # print the repo root (LIFECYCLE.md, templates/, examples/ live there)
```

| Subcommand | Stage | What it does |
|---|---|---|
| `falsify reality`     | 1.5 | Can the data support the claim? Power (min detectable effect at n), label-noise precision ceiling; or CSV mode (n, balance, missingness, gold disagreement). |
| `falsify leakage`     | 1   | Train/test hygiene: duplicate-across-split, temporal overlap, group leakage (hard fails); perfect-predictor (suspect, human review). |
| `falsify value`       | 2.5 | Economics: gross gain, annual net, payback period → PASS / FAIL (the "1% lift, $2M deploy" kill). |
| `falsify planted`     | 4   | Prove your evaluation harness can detect a planted signal and reject noise. `--metric auroc\|pearson\|spearman`. |
| `falsify closed-loop` | 5   | Correlate the model's score with an **independent** oracle; detect closed-loop measurement. |
| `falsify prereg`      | 2   | Date-lock TRUE/FALSE shapes + thresholds before you look at results. |

Examples:

```
# Idea stage — can 90%-precision ever work if my labels are ~15% noisy?  (DO NOT PURSUE)
falsify reality --label-error-rate 0.15 --required-precision 0.90

# Idea stage — is a 150-case pilot powered to detect a correlation of 0.3?  (PASS)
falsify reality --n 150 --target-effect 0.3

# Data stage — is my train/test split leaking by customer?
falsify leakage --data data.csv --split-col split --group-col customer_id --label-col churn

# Economics — each unit worth $2k, expect +1 unit, build $500k, upkeep $80k/yr  (FAIL)
falsify value --value-per-unit 2000 --expected-lift 1 --deploy-cost 500000 --annual-maintenance 80000
```

Each subcommand has its own `--help`.

---

## The `/falsify` Claude skill (guided)

In Claude Code, type `/falsify` (or just describe an ML idea / claim). It walks the ten stages —
running the CLI where you have data, interviewing you where you only have an idea — and fills in a
[`templates/feasibility_card.md`](templates/feasibility_card.md) with a top-level
**PURSUE / DO NOT PURSUE / INSUFFICIENT EVIDENCE** verdict.

`PURSUE` means *worth investing further*, not *ship the model* — the model still has to survive Stage
5 falsification on real data before any claim is trusted.

---

## The ten stages

See [`LIFECYCLE.md`](LIFECYCLE.md) for the full map. Each stage emits PASS / FAIL / UNKNOWN; they roll
up to the verdict. Critical stages (a FAIL is decisive): 0, 1, 1.5, 2.5, 5.

| # | Stage | Tool / template |
|---|-------|-----------------|
| 0 | Frame the problem | `templates/framing.md` |
| 1 | Data contract + leakage | `falsify leakage` · `templates/data_contract.md` |
| 1.5 | Data reality | `falsify reality` · `templates/data_reality.md` |
| 2 | Baseline before training | `templates/baseline.md` |
| 2.5 | Value / economics | `falsify value` · `templates/value_case.md` |
| 3 | Training health | `templates/training_health.md` |
| 4 | Eval design | `templates/eval_design.md` |
| 5 | Falsify the claim | `falsify planted` · `falsify closed-loop` · `falsify prereg` · [`PROTOCOL.md`](PROTOCOL.md) |
| 6 | Deploy + monitor drift | `templates/monitoring.md` |
| 7 | Stopping rule | `templates/stopping.md` |

---

## Worked examples

[`examples/`](examples/) has runnable end-to-end walkthroughs:
`bash examples/classification_spam/run.sh` (binary classification, AUROC) and
`bash examples/regression_demand/run.sh` (regression, Pearson).

---

## Tests

```
python3 -m pytest tests/          # full suite
python3 tests/test_data_reality.py # any single file runs without pytest, too
```

Every diagnostic is validated against hand-derived or scipy-cross-checked values; the power math is
bit-accurate vs scipy. The CLI and installer are tested too (the installer runs against a throwaway
temp HOME, never your real `~/.claude`).

## License

Apache License 2.0 — free to use, modify, and redistribute (including commercially); keep the
`LICENSE` and `NOTICE` files and state any changes you make. Includes an explicit patent grant.
See [LICENSE](LICENSE) and [NOTICE](NOTICE).

---

*Methodology only — no proprietary model, data, or result. The diagnostics run on your own project.*
