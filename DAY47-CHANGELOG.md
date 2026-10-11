# Day 47 changelog — SnapMatch

## Finding

`metrics()` re-pulled and re-scanned every decision+outcome the system had
ever logged, on every call — Guide 5's Mistake 5. Unlike the other repos'
`learn()`, this isn't called from the feedback path (`review()` /
`record_return()`); it backs the `/metrics` API route in `app.py`, i.e. a
dashboard endpoint that can be polled on a schedule. A polled dashboard
re-scanning the full history on every poll is the same mistake with a
different trigger.

## Changes

- `gen4/memory.py`, `gen4/feedback.py` — kernel fix (shared across the
  portfolio; see LendFair's changelog): `fact_history`,
  `decisions(outcome_since=...)`, the `outcome_ts` fix, the
  `(system, ts DESC)` index, and the `new_rows_since` / `mark_processed` /
  `accumulate` primitives.

- `service.py`
  - `metrics()` rewritten (`METRICS_KEY = "snapmatch_metrics"`,
    `METRICS_GRACE_DAYS = 1`): pulls only outcomes since the last
    watermark via `new_rows_since()`, and merges reviewed/mismatch/
    published/missed-mismatch-return deltas into running totals via
    `accumulate()` instead of re-deriving them from the full decision
    history on every poll.

- `tests/test_incremental_learning.py` — new, 3 tests: idempotency across
  repeated polls with nothing new, picking up new outcomes after more are
  recorded, and a direct cross-check of the incremental totals against an
  independent from-scratch recompute straight from `memory.decisions()`
  (what `metrics()` used to do) to prove mathematical equivalence.

## Verification

- `pytest -q` → 16/16 passed (13 original + 3 new).
- `run_evals.py` → GATE PASS, 100%/100%, unchanged.
- `seed.py --reset` → identical to pre-fix baseline (600 listings, 76 true
  mismatches, thresholds per category unchanged).
- `run_demo.py` → identical output (4/8 listings flagged, same category
  mismatch-return prioritization).

No behavioral change in any observable output.
