# DEV_AUX task2618 — shared AlphaBeta/Receipt WDL cost scan

**Status: bounded cost feasibility completed; science remains OPEN.** This is
not a WDL strength comparison, a full training run, or evidence of convergence.

## Frozen procedure

The write-once plan was registered before search at
`results/dev_aux/task2618/wdl-shared-cost/plan.json` (SHA-256
`e47135d301a0ad0be8083656e39cf55bed7ffe185c73a9953b24b4f6f163347f`). It
bound the active DEV_AUX session, all runner/adapter/search/restore/stop-reader
source hashes, the task2619 training-root manifest, four fixed seeds, and the
following controls: first 32 exact eight-ply training roots only (8 per seed),
uniform fixed-foe weights, the shared task2612 AlphaBeta/Receipt search at
D2/q0, one combined candidate-plus-foe cap of 100,000 nodes per seed, 8
proposal rounds, 8,192 nodes / 2 seconds per search, and a 900-second global
wall cap. No evaluation roots were read. The four episode order was incumbent
as White, proposal as White, proposal as Black, incumbent as Black on one root.

Actual terminal labels and proposal acceptance were used in memory by the
registered WDL update; the persisted records contain only search/node cost,
terminal-versus-unknown censoring, and timing. They contain no W/L/D labels,
intervals, acceptance decisions, proposal vectors, or learned coefficients.
UNKNOWN stayed a full `[-1,+1]` endpoint, and an incomplete four-game block
could not update the in-memory incumbent.

## Result and audit

The scan completed all four 100,000-node cost arms in 53.134 seconds total:
400,000 paid nodes, 3,562 searches (3,558 complete and 4 incomplete), 20 game
slots, 16 actual terminal episodes censored from persistence, and 4 unknown or
partial episodes. Each seed completed one full paired block; remaining slots
were incomplete/censored at the registered resource boundary. Thus the status
`COMPLETE_COST_ONLY` means the registered cost scan completed, not that the
eight proposal rounds or a strength sample completed.

The post-run artifact audit passes: write-once hashes reconcile, every row is
within the combined per-seed cap, recorded nodes equal candidate plus foe
nodes, and no outcome/weight field is persisted. The seven adapter tests, one
prior source-bound feasibility test, and three new artifact tests pass (11
focused tests total). `py_compile` and `git diff --check` also pass.

## Updated all-in estimate

The previous source-bound estimate was 93.473 minutes, including a 25% runtime
margin and 900-second setup/audit reserve; it used 494.221 seconds for 4M WDL
training nodes from the older `TrainingSearch`. This scan measured 400,000
shared-path WDL nodes in 53.134 seconds. Linear scaling gives 531.339 seconds
for 4M nodes. Replacing only that historical WDL cost yields a revised
94.247-minute estimate. This scaling is a planning estimate, not a runtime
guarantee; the shared path is now measured, but only over a 400,000-node cost
panel. The existing 110-minute all-in hard cap is unchanged, leaving 25.753
minutes between the revised point estimate and the cap, and the estimate stays
below the 120-minute Dot-assessment threshold. No Dot assessment is required
for this scope.

Do not treat this result as a registered full comparison. Before starting one,
freeze and hash the complete training/evaluation plan, including all roots,
foe, learner endpoints, shared-cost accounting, evaluators, audits and cap
semantics. Preserve missing slots and UNKNOWN; do not resume or top up this
cost scan. Evidence files are `registration.json`, `started.json`,
`episodes.jsonl`, `result.json`, `test_shared_wdl_cost_scan.py`, and this report.

## Superseding common-path estimate (2026-10-20)

The above 94.247-minute estimate was itself incomplete: it replaced the WDL
timing but retained historical TreeStrap/TDLeaf timings from different runs.
Task2612 attempt-4 provides 400k-node cost-only receipts for both TreeStrap and
TDLeaf on the same shared AlphaBeta/Receipt candidate-vs-fixed-foe path. Scaling
those and the WDL scan to 4M nodes per method gives 565.267s, 554.453s, and
531.339s. With the slower complete evaluation panel, 25% margin and 900s
reserve, the updated estimate is 95.768 minutes. It remains below the unchanged
110-minute cap and 120-minute assessment threshold; actual runner/root mix may
differ. Reproducible details and embedded runner-source verification are in
`FEASIBILITY.md`, `feasibility.py`, and `feasibility.json`. No learner run has
been registered or launched.
