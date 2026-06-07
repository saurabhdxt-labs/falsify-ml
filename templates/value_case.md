# Stage 2.5 — Value / Economics Case — <project/claim name>

> Lifecycle stage 2.5 of 7+. See ../LIFECYCLE.md.
> A project can be scientifically sound and still not worth building. This stage asks: do the
> economics work? Fill the numbers, then feed them to `scripts/value_check.py`.

**Date:** <YYYY-MM-DD>

## The current process (the thing the model would replace/augment)
- What is done today without the model: <...>
- Its cost per period (people, tools, errors): <...>
- Its performance today (the baseline this model must beat to add value): <...>

## Value of improvement
- What is **one unit of improvement** worth? (one fewer error, one more conversion, one hour
  saved): `value_per_unit = <...>`
- How many units of improvement is the model expected to add per period (be conservative — use the
  Stage-2 minimum lift, not the optimistic one): `expected_lift = <...>`

## Cost to build and run
- One-time build + deployment cost: `deploy_cost = <...>`
- Ongoing cost per period (maintenance, retraining, monitoring, infra): `annual_maintenance = <...>`

## Run the check
```
python3 ../skills/falsify/scripts/value_check.py \
    --value-per-unit <...> --expected-lift <...> \
    --deploy-cost <...> --annual-maintenance <...>
```

## Verdict (from the tool)
- Gross gain / period: <...>
- Annual net (after maintenance): <...>
- Payback period: <...>
- **Stage 2.5 status: < PASS | FAIL | UNKNOWN >**
  - PASS = gains cover ongoing cost and the build investment recovers.
  - FAIL = even with the expected lift, gains don't cover cost — DO NOT PURSUE on economics alone,
    regardless of how good the model is.
  - UNKNOWN = one or more numbers not yet known.

**The cheapest NO-GO of all: a project that can't pay for itself, killed before any model is built.**
