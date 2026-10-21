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
44 completed UNKNOWN and 0 missing). These completed-run figures are useful
separate runtime comparators. The task2636 projection instead inherits
task2621's slowest 80k-node cost-scan arm with a1.5× training margin
(2,110.568s) and task2609's measured 1,536-slot evaluation (691.419s), as
reconstructed in `estimate-basis-receipt-verification-v2.json`. The projected
4,001.988s is 2,598.012s below the6,600-second lifetime cap, but is not a
runtime guarantee for the16 candidate rules and omits unresolved adapter and
whole-result validation costs.

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

## Reusable partial-audit surface check (2026-10-21)

The nearest working partial-training precedent is task2623's
`audit_partial_training.py`: it replays closed episodes and a trailing open
episode, reconstructs TD updates and checks node accounting, but is coupled to
four numeric rule IDs, their rule files, a rule/seed arm prefix and a fixed
interruption correction. It is a source pattern for candidate-index handling,
not a candidate-index auditor that can be called unchanged. The new arm key
must also bind the candidate-index row, candidate seed, ten-coordinate model
snapshot and that candidate's frozen full-history roots.

The task2636 `partial_evaluation_audit.py` already supplies tested
candidate-index-aware slot enumeration, row/cap validation, partial
UNKNOWN-versus-missing bounds, one-query full-history replay, and a reused
source-pinned replay context. Its `audit_files` binds the frozen plan and root
pool and rejects non-newline-terminated slot rows; its current receipt checker
explicitly does not validate source hashes or replay. It does not yet compose
registration, completed training result, independent training audit,
write-once evaluation binding, slot/query file hashes and the final result
receipt into the complete artifact chain described in
`WHOLE_RESULT_AUDITOR_INTERFACE_REVIEW.md`.

The focused existing suite `test_partial_evaluation_audit.py` passed all 10
tests in the checkout's `.venv`. This verifies the present structural,
partial-bound and replay primitives; it does not test a producer, durable
stop closure, whole-bundle binding or any task2636 output. The exact source
comparison narrows the implementation target to candidate-index training
production/audit, stop-safe lifecycle integration and an outer receipt-bundle
orchestrator. It still supplies no measured engineering duration, so it does
not close the remaining preparation reserve or authorize registration.

## Evaluation query-budget field review (2026-10-21)

The frozen plan has one explicit search object at `training.search`:
AlphaBeta D2/q0,2,048 nodes and2.0 seconds per query. Its evaluation object
repeats depth2 and H=128 but has no `nodes_per_query` or `seconds_per_query`
field. The existing task2636 replay adapter nevertheless reads
`plan["training"]["search"]["nodes_per_query"]` when auditing evaluation
queries, and focused tests bind `requested_nodes=2048`; therefore the current
tested adapter treats the training search object as a shared execution
contract. This is an implicit cross-phase convention in the frozen document,
not a separate evaluation cap. Future registration/runner code must follow
that exact shared contract or expose an audited contract mismatch before any
run; do not infer a different evaluation query cap. The plan, auditor and test
hashes are `a3af462f9db4018118619aea9d79374e7e876f83735559d8269a80b506c73c40`,
`e894da78fd22d06771419fb4003685fff6df5413ea59725d2321ed81399ef8ca`, and
`f5471b1049d49701b56fbb99ee669af5b71a8e5c642f2a4193bf6677cecf3fa9`.
No evaluation search or slot was started.

The executable outcome-blind contract check is saved as
`evaluation-query-budget-contract-audit.json`. It rehashes the frozen plan,
evaluation adapter, focused tests and full-pool screen; confirms that evaluation
has no separate per-query node/time fields; confirms the adapter passes the
shared `training.search.nodes_per_query` value and tests bind 2,048; and verifies
registration, search and `run-v1` remain absent. The first run exposed a brittle
source-text check that expected an obsolete argument sequence; after matching
the current replay call and explicit `requested_nodes` fixture, compile and
audit passed, followed by 10/10 focused tests. This closes only the budget
convention question; it does not validate a future runner or infer actual cap
hits, UNKNOWN frequency or cost.

### Correction: node limit is verified; evaluation time limit is not

The first contract receipt (`evaluation-query-budget-contract-audit.json`)
overstated the shared convention by listing the training value of2.0 seconds
alongside the evaluation node limit. The evidence supports only the node limit:
the replay adapter passes `training.search.nodes_per_query`, and focused tests
bind `requested_nodes=2048`. The task2636 adapter does not invoke search and
does not consume `seconds_per_query`; there is no task2636 runner yet. The
task2625 reference evaluator does pass its own plan's shared search seconds,
but it is not a task2636 implementation. The corrected write-once receipt is
`evaluation-query-budget-contract-audit-v2.json`: node cap verified, evaluation
seconds-per-query binding unverified. Before registration, the new runner and
tests must explicitly bind the intended evaluation time policy or establish
that only the cumulative evaluation/lifetime caps apply. The frozen plan was
not modified, and no search was run.

One additional receipt hazard is a coincidental count match: the completed
task2625 training result has16 `(rule, seed)` arms, as task2636 has16 candidate
arms, but the saved task2625 final vectors are all six-dimensional. Task2636
requires a candidate-index key and ten-dimensional vector per candidate.
Therefore an arm-count-only check or direct reuse of the reference result is
invalid; the candidate-index training auditor must bind each row to the
candidate seed and rule hash and require exactly ten finite weights. See
`RECEIPT_BINDING_CROSSWALK_20261021.md` for the pinned schema comparison.

The lifecycle budget separately assigns evaluation a3,000-second stage cap
within the6,600-second global cap. The task2636 partial replay schema checks
node requests/counts and does not validate per-query elapsed time. By contrast,
the pinned task2625 reference passes `seconds_per_query` to AlphaBeta and stores
the returned `receipt.seconds` in each query row; its source hash matches the
reference hash in task2636's frozen lineage. This supports a concrete future
acceptance check: the registration-pinned task2636 runner must either use the
frozen `training.search.seconds_per_query=2.0` as its evaluation search time
bound and preserve the search receipt, or explicitly declare and test a
node-only policy under the evaluation/global wall-clock caps. No choice is
currently implemented or verified, so registration remains closed.

## Frozen evaluation-root node-bound screen

Because the current replay contract verifies the shared 2,048-node query
request, the matching no-search structural screen was extended to all256
frozen evaluation roots (16 families for each of16 candidates). The
unpruned/no-terminal-shortcut D2 call bound exceeds2,048 for76/256 roots
(29.69%); median1,204, mean1,636.9, p90 3,717, maximum8,659. This is close to
the training pool's549/1,920 (28.59%), so the earlier warning is not obviously
an eight-root or training-only sampling artifact. Candidate heterogeneity
remains substantial: candidate0 has15/16 above the bound; candidates14 and15
have0/16. These are not actual AlphaBeta cap hits, UNKNOWN outcomes, or runtime
estimates; pruning, terminal short-circuiting, endpoint models and color do not
enter this full-width count. The screen compares against the maximum 2,048-node
query request; the planned runner must reduce a later request to the remaining
slot nodes when that is smaller, a case this root-only census does not model.
The evaluation per-query seconds policy remains unverified. Evidence and source pins:
`query-cap-evaluation-fullpool-audit.json` and
`audit_eval_query_cap_fullpool.py`.

The per-candidate training/evaluation exceedance fractions are closely aligned
in this descriptive n=16 comparison (Pearson r=0.963; Spearman rho=0.971 with
average tied ranks), using 120 training roots and16 evaluation roots per
candidate. Candidate0 is high in both phases (112/120;15/16), while candidates
2,9,14,15 are zero in both; candidate10 is a visible phase difference
(56/120 vs12/16). This supports candidate-persistent structural heterogeneity
in the fixed roots, not an independent sample, causal estimate or prediction of
actual search/censoring. Receipt:
`query-cap-phase-alignment-audit.json`.
