# Task2636 runner contract review

The task2625 runner is a method reference, not an executable consumer of this
new pool. Its frozen sources must remain unchanged. Direct reuse would fail
closed or misbind records for concrete reasons:

* `train.py` and `evaluate.py` pin `RULES=(271001,271002,271003,271004)`,
  four task2625 rule JSON paths, the task2624 pool and the task2625 run
  directory. Task2636 roots instead identify candidates by `candidate_index`
  and carry `candidate_seed`, `rule_path`, and complete `record` data.
* The earlier four-rule panel has six fixed-scale feature coordinates. The
  task2636 candidates have a common ordered ten-channel vector, so the
  seed-1977 initial model has ten coordinates (fixed coordinate zero plus
  nine uniform coordinates). Reusing the old serialized vectors would fail
  dimensional validation and would not represent this domain.
* The task2625 trainer expects the four-by-four rule/seed grid, while the new
  design has sixteen candidate arms and one seed per candidate. It must bind
  candidate identity, model weights, root family, episodes and query rows
  together throughout logging and independent replay.
* The task2625 evaluator allows a 3,600-second evaluation stage. Combined with
  the unchanged 2,400-second training cap and 1,200-second prep/audit/reporting
  reserve, this would permit 7,200 seconds. The new design's 3,000-second
  evaluation cap is required for the 6,600-second total; it must be enforced
  by a cumulative deadline that also includes validation and reporting.
* Existing write-once registration and non-retry rules are useful controls,
  but a new registration must bind task2636's pool/audit, all sixteen
  candidate rules and the adapted train/evaluate/audit sources before creating
  any run receipt. The execution directory must be the absent
  `results/dev_aux/task2636/run-v1` path, with write-once receipts.
* The task2625 training and evaluation auditors require complete runs, and its
  analyzer rejects a partial evaluation. They cannot independently qualify a
  cap-stopped task2636 result. New partial auditors must replay all durable
  episodes/queries and completed slots; the analyzer must enumerate all512
  predeclared pairs, keeping completed UNKNOWN endpoints distinct from missing
  slots while bounding either absent reward over[-1,+1].

Cancellation needs a separate adapter. Pinned task2492 AlphaBeta polls its
cancel callback every128 nodes and converts `BudgetEnd` into an incomplete
receipt that includes visited-node count. The role stop reader instead raises
`PersistentStop`; allowing that exception to escape mid-search can close the
JSONL streams but skip the final `training-result` or `eval-result`. A future
runner should catch the role stop at the search poll, translate it to the
search's incomplete receipt, write the UNKNOWN query/episode or slot, emit a
`STOPPED_USER` result, flush/close files, and then stop before another sample.
The same callback should check the shared monotonic deadline. If the process is
hard-killed before that closure, recovery records `NO_FINAL_RECEIPT` from the
write-once start record and durable log prefix; it never retries. Source pins
for the search/learner and stop reader are included in the machine audit.

For hard interruptions, recovery should only parse newline-terminated JSONL
rows, preserve a truncated trailing byte range as evidence, and mark any slot
without a closure record as missing. Flush query rows as written; fsync closed
episodes/slots and phase/final receipts (rather than every search row), counting
that cost against the fixed reserve. A `started` record with no final result is
`NO_FINAL_RECEIPT`; raw lines remain immutable and are never used to resume the
run.

The separate task2636 implementation must preserve the task2625 learner and
resource semantics: fixed coordinate zero and scale ten; deterministic
uniform initialization; 120 full-history training roots per candidate;
250,000 combined candidate/foe nodes per candidate; depth two search; H=128;
terminal-only reward; candidate and foe node accounting; exact query and
episode journaling; two learner colors and two endpoints; the balanced 20k /
40k combined two-side node caps; and independent replay before any result
analysis. It must emit explicit incomplete-arm, UNKNOWN, and missing-slot
states at caps, never infer a draw, retry, top up, or extend after seeing
results.

The pinned task2625 receipts measured 1,750.237s for 4M training nodes and
3,693 episodes, then 555.656s for 1,024 evaluation slots (1,254,951 nodes,
44 completed UNKNOWN and 0 missing). The task2636 projections are 2,110.568s
for training and 691.419s for evaluation, leaving 289.432s and 2,308.581s
respectively below the proposed stage caps. These are projections against a
different four-rule panel, not a runtime guarantee for the 16 new candidate
rules. The overall projected 4,001.988s is 2,598.012s below the 6,600-second
lifetime cap.

The projected task2636 preparation/audit allocation is 542.632 seconds of the
1,200-second lifetime reserve, leaving 657.368 seconds for future replay,
analysis, and reporting. That amount is a conservative budget charge, not a
measured elapsed-time claim. The remaining future allowance is 6,057.368
seconds, including the 2,400-second training and 3,000-second evaluation
stage caps. The future run must stop gracefully at that cumulative allowance
and retain all partial evidence. If training is incomplete, evaluation is marked
not started and its 1,024 planned slots remain missing, not draws. A cap hit
during evaluation writes the completed rows and enumerates each missing slot.
Any completion bounds use the full predeclared512-pair denominator and keep
UNKNOWN and missing counts distinct.

## Stop-poll coverage addendum (2026-10-21)

A source-site replay found that the task2625 reference consumers call the stop
reader outside AlphaBeta as well as through its `cancel` callback: training
polls before each arm, before each episode and before each ply; evaluation polls
before the run and before each slot. Therefore translating `PersistentStop`
only at the in-search callback is insufficient. A task2636 adapter must latch
stop/deadline state at every poll site or catch it at the run boundary, flush
the state that actually exists, write a final `STOPPED_USER` receipt and start
no subsequent sample. If a slot has started but no scored terminal is reached,
close it as UNKNOWN; if a slot has not started, retain it as missing. Do not
invent a query for a pre-query stop. Keep hard-kill `NO_FINAL_RECEIPT` recovery
distinct. Exact pinned poll sites and source hashes are in
`stop-poll-site-audit.json`. The frozen task2625 sources and task2636 design
plan remain unchanged; this addendum must be included in any future runner
registration and independent audit.

The 1,200-second reserve must cover all charged preparation/audits plus
post-run replay, analysis and report work; if that allocation proves
insufficient, finish with a partial report rather than consume another stage
or exceed the global ceiling.

No new runner, registration, training or evaluation was created in this
review. The next admissible step is a separately reviewed source-bound
preflight contract and an all-in estimate that includes the already completed
task2636 root work; registration remains a later explicit, write-once action.
