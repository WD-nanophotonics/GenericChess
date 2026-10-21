# task2636 receipt-binding crosswalk

## Reference chain verified

The seven task2625 reference artifacts named by the task2636 design were
re-hashed read-only and matched their recorded pins: plan
`9cca31fae284f8f88120a58c8128294455346f1a1bc4c813a30c12cf111e0b3f`,
registration `340b1decf71cabd5d21ced72aec92739b7250d8392470ad1c2744c04772231ec`,
training result `760bb829c2f0424b6e780f1541a6fe70fe7b824c998b0671e5c9794108b84304`,
training audit `87d09877ca88d473d44ec472f3de62085f2fdea7a1d9998b9e7a529f69210439`,
evaluation registration `abf7431f492d907c1c2c5a556e06c193447ac81476e379c4d1d922d057801d65`,
evaluation result `e4ac648f12a4609d19e6176cb1a0c7406c24b6ed0e34f7f51f28f332481dd1f9`,
and evaluation audit `84114fc0910e8cc1492f7b8624d722b2849d45b69ba15995e44b13731d62c`.

The reference records demonstrate a concrete chain: registration pins plan,
pool/audit and sources; training result binds plan and registration and contains
per-arm `final_weights`; training audit binds the result and plan; evaluation
registration then binds registration, plan, training result and training audit;
evaluation result records completed/UNKNOWN/missing counts; the independent
evaluation audit binds the final result hash and replay totals. Its result is a
method reference only: rule IDs, six-coordinate vectors, complete-run auditors
and the task2625 pool are not task2636 inputs.

The completed task2625 `training-result.json` has status COMPLETE and16 arm
rows, but every `final_weights` vector has six coordinates and each row is
keyed by `(rule, seed)`. Task2636 also plans16 rows, but its keys must be
candidate indices0–15 with candidate seed/rule lineage, and every model has ten
coordinates (one seed-1977 initialization shared across candidates). Equal row
count is therefore a misleading superficial match; neither task2625's complete
result nor task2623's four-rule partial audit can supply a task2636 candidate
model receipt. The future handoff must independently bind all16 candidate
indices, candidate-rule hashes, seed-1977 initial vectors and ten finite final
weights before evaluation.

## task2636 gap established from current source

`partial_evaluation_audit.py` exposes three separate operations:
`audit_completed_rows`, `validate_result_receipt`, and
`FrozenSlotReplayContext.replay`. `audit_files` only loads the pinned plan and
root pool plus a newline-terminated slot file. The receipt validator checks
plan, registration, training-result and root-pool hash syntax and row/query
totals, but explicitly does not check source hashes, legal replay, terminal
authority or time evidence. The replay context binds plan/root/candidate/rule
and runtime inputs, but receives `expected_weights` and `foe_weights` from its
caller. No current entry point verifies the complete registration → training
result → independent training audit → evaluation binding → final result chain
before passing model vectors into every closed slot. This matches the existing
pre-registration matrix: the primitives are present, the bundle/orchestration
gate is not.

The only saved exact-candidate history source is also not a substitute bundle
fixture: its 64 task2635 episode rows contain a full history, ending, candidate
index and seed, but no planned evaluation-slot endpoint, per-query receipts,
bound ten-weight snapshot, evaluation binding or final slot/query file hashes.
All 64 are UNKNOWN endings. It can inform a separate history replay check, but
cannot exercise the task2636 end-to-end evaluation auditor or its actual-terminal
branch.

The pinned task2625 consumers also confirm why stop behavior needs an adapter,
not just a `cancel` callback. Training calls the persistent reader before each
arm and ply; those outer calls are outside a closure handler. Evaluation polls
before the run and within each slot's `try`, but the enclosing
`except BaseException` re-raises, bypassing that slot's final row. Both streams
flush JSONL rows, while the reference writers do not fsync each closed episode,
slot, or final receipt. The search poll can return an incomplete `BudgetEnd`
receipt, but `PersistentStop` at an outer poll still aborts the consumer. Thus
the required work is not only candidate-key substitution: it also includes
latched stop/deadline state, closure policy, durable-write boundaries and tests
for each poll site. This is a source-level control-flow finding; no stop was
raised and no output was written.

## Minimum integration acceptance

Before any task2636 registration, a future orchestrator and tests must establish
all of the following from exact bytes, rather than caller assertions:

1. Validate paths remain within this checkout; verify plan, registration,
   root-pool, candidate-index, candidate-rule, adapted-source, training-result,
   training-audit, evaluation-binding, slot/query and final-result hashes.
2. Require the independent training audit to be COMPLETE and bind the exact
   training-result and plan hashes. Require exactly one ten-finite-weight model
   snapshot for each candidate index and verify its seed/rule/root lineage.
3. Verify the write-once evaluation binding names those exact snapshots and
   hashes before the first evaluation slot; derive each endpoint vector only
   from that binding or the frozen seed-1977 initialization. Keep the opponent
   fixed to ten ones.
4. Read only newline-terminated JSONL rows, preserve incomplete trailing bytes,
   verify slot/query file hashes against the final receipt, then compose
   structural validation and one reused frozen replay context over every closed
   slot. Keep all 1,024 slots and 512 pairs; report actual terminal, completed
   UNKNOWN and missing separately.
5. Exercise empty/missing-only input, a legal completed UNKNOWN, malformed or
   duplicate rows, hash drift, a mismatched trained model, and stop/deadline
   exits before arm, episode, query, inside search and between slots. A real
   `ACTUAL_TERMINAL` closure remains separately untested: see
   `TERMINAL_FIXTURE_SOURCE_REVIEW_20261021.md`.

The existing task2625 hashes bound the reference schema, not the amount of new
implementation or its runtime. No new registration or output schema exists to
measure. Therefore no defensible numeric estimate for the missing integration
or its validation was produced here. Keep task2636 unregistered and preserve
the fixed 6,600-second experiment cap; the 66.70-minute execution projection is
not a complete all-in estimate. This review ran no model, search or evaluation
and changed no frozen inputs.

## Reuse-gate source spot-check — 2026-10-21

A direct source spot-check confirms none of the four open integration groups
can be marked closed by citing the task2625 implementation alone:

* `train.py` keys arms by `(rule, seed)` and emits the six-coordinate task2625
  model. Task2636 requires `(candidate_index, candidate rule hash)` lineage and
  ten coordinates; a task2636 training producer and full-arm auditor remain
  absent.
* `evaluate.py` supplies the task2625 per-query time limit and node limit, but
  its model handoff and complete-result closure are bound to the task2625
  training artifact. The task2636 replay primitive accepts caller-supplied
  endpoint weights and only replays a row; a whole-chain orchestrator that
  checks every registration/result/audit/source hash is still missing.
* The task2635 candidate-history file available for source review contains
  UNKNOWN endpoints, not a task2636 actual scoring-terminal closure fixture.
  The frozen task2636 roots themselves have no root-legal promotion, so those
  roots cannot supply such a fixture without a separately justified history.
* Task2625 producers flush JSONL rows (`train.py` and `evaluate.py`) but do not
  fsync each episode/slot or final receipt. Evaluation's outer stop poll and
  `BaseException` re-raise do not close an in-flight slot. Durable stop/deadline
  handling therefore needs an adapter plus interruption tests.

These are boundaries of the pinned reference implementation, not evidence of
task2636 runtime or an actual failure during a task2636 run. The cheapest
decision-changing conclusion is that source reuse alone cannot satisfy any of
the four remaining gates; new candidate-index, whole-bundle, terminal-fixture,
and stop/durability work must be scoped and costed before registration. Costs
remain unknown, so the frozen reserve cannot be asserted sufficient and no
registration is authorized by this review. Source anchors: task2625
`train.py:106-225`, `evaluate.py:107-208`; task2636
`partial_evaluation_audit.py:448-519`; exact frozen hashes are retained in the
existing pre-registration and receipt crosswalk records.
