# DEV_AUX task2617 — fresh-root Chess evaluation-cap feasibility

**Status: feasibility only.** No experiment is registered or started; no games,
search queries, or model updates were run for this task. Science remains OPEN.
This status describes the feasibility checkpoint sealed before evaluator
implementation; any later pre-run registration and execution state is recorded
separately in the immutable `run-001/registration.json` receipt.

## Question and frozen proposal

On a fresh standard-Chess panel, does increasing the per-game cap from 20,000
to 40,000 nodes paid by both sides reduce UNKNOWN and change the actual W/D/L
contrasts among the task2616 frozen `initial`, `TD`, `WDL`, and `TreeStrap`
endpoints?

The proposal keeps the four task2616 seeds, uniform fixed foe, both colors and
all four endpoints. It uses 32 new eight-ply families (1,024 slots). A fixed
seed (`26170001`) assigns 16 whole families to each cap; every endpoint, seed,
and color within a family receives the same cap. A second fixed seed
(`26170002`) freezes all 1,024 slot execution order independently of outcomes,
so a global cap does not process low- and high-budget families as contiguous
blocks. This makes the cap comparison a randomized family-level contrast and
preserves within-family learner pairs.
Known terminal W/D/L stays fixed; UNKNOWN is censored and completion bounds vary
only UNKNOWN endpoint rewards over `[-1,+1]`. Report UNKNOWN rates, W/D/L,
endpoint completion bounds, and the finite-panel cap contrast separately. The
deterministic root panel does not support population or confidence-interval
claims.

## Outcome-blind root check

`feasibility.py` reads only `initial_record` from registered Chess evaluation
logs; it does not inspect outcomes or post-root actions. It reconstructs all
5,000 possible task2616 training-family roots from the frozen recipe, excludes
all 218 distinct registered Chess evaluation histories and all 32 task2616
evaluation roots, then selects the first 32 unique valid records in family
range `[710001,720000]`. All 32 were available immediately. Exact full-record
overlap is zero against each exclusion set. Each record includes initial FEN
and ordered eight-ply UCI history; its SHA is saved in `prospective-roots.json`.
The complete plan, random assignment, source hashes and cost calculation are
in `feasibility.json`; the slot order is also saved in `execution-order.json`.

## Cost estimate and execution gate

The planned slots have a maximum of 30.72M paid nodes: 512 slots at 20k and 512
at 40k. Task2616 evaluated 1,024 slots using 14,648,460 nodes in 1,883.679s.
Linear scaling projects 3,950.4s for the new maximum-node total; a 25% runtime
margin plus a 900s setup/audit reserve yields 5,837.9s (97.3m). A prospective
5,400s (90m) evaluation cap plus the same reserve yields 6,300s (105m), below
the user's 7,200s consultation threshold. This is a projection, not a runtime
guarantee; different query lengths, nonlinear search cost and concurrent load
can affect it. Missing slots must remain missing if the cap binds.

Before any run, implement and test a separate evaluator that applies the
frozen family assignment and binds its complete source hashes. Register its
slots, source pins, seeds, roots, costs, and analysis before outcomes. If the
revised all-in estimate reaches 120m, obtain Dot's necessity assessment before
starting; do not split or expand this cap study. Do not modify or extend task2616.

## Reproduction

From the DEV_AUX checkout, run:

```powershell
.\.venv\Scripts\python.exe results/dev_aux/task2617/feasibility.py
```

The script deterministically rewrites `feasibility.json`,
`prospective-roots.json`, and `execution-order.json`; it does not execute the
proposed experiment.

## Evaluator implementation checkpoint

The separate `evaluate.py` enforces the frozen family-level combined-both-side
node cap, shuffled slot order, a 90-minute global cap, full-history replay, and
source/model/runtime pins. `analyze.py` verifies receipts and paid-node totals,
keeps missing or UNKNOWN outcomes censored, and reports endpoint-specific
finite-panel reward and paired-contrast bounds. `register_run.py` writes a
pre-run bundle exclusively; the evaluator refuses unregistered or changed plans.
Nine focused standard-library tests pass with no real games or searches started;
one synthetic all-terminal fixture exercises the complete report path.
This implementation checkpoint remains unregistered until all code and tests
are frozen and their hashes are recorded.
