# task2636 whole-result auditor interface review

## Minimum composition

The frozen evaluation cannot be audited safely from `eval-result.json` alone.
The future audit entry point should receive explicit paths for: plan, write-once
registration, completed training result, independent training audit, pre-slot
evaluation binding, slot JSONL, query JSONL, and final evaluation receipt. It
must verify each file's SHA-256 against the downstream receipt/registration
before parsing it. Paths must resolve inside this checkout; JSONL rows only
count when newline-terminated.

The task2625 source pattern stores each arm's `final_weights` in
`training-result.json`; its `training-audit.json` returns PASS and binds both
the training-result SHA and plan SHA; `evaluation-registration.json` binds the
registration, training-result and training-audit hashes. Task2636 must preserve
that sequence but use candidate-index/rule hashes instead of task2625's numeric
rule IDs. The training result must expose one ten-weight final snapshot per
candidate index. The independent training audit must be COMPLETE and bind both
the exact training-result SHA and plan SHA. Evaluation binding must be
write-once, require that audit, and bind registration, plan, root pool, training
result and training-audit hashes before the first slot. The TDLeaf evaluation
model comes only from that bound candidate-index snapshot; the `initial`
endpoint is recomputed from the plan-pinned seed-1977 source; the opponent
remains the fixed all-ones model.

The inspected reference bytes still match the task2625 source pins: plan
`9cca31fae284f8f88120a58c8128294455346f1a1bc4c813a30c12cf111e0b3f`, training
result `760bb829c2f0424b6e780f1541a6fe70fe7b824c998b0671e5c9794108b84304`,
training audit
`87d09877ca88d473d44ec472f3de62085f2fdea7a1d9998b9e7a529f69210439`, and
evaluation binding
`abf7431f492d907c1c2c5a556e06c193447ac81476e379c4d1d922d057801d65`. They
demonstrate the existing receipt linkage only; they do not instantiate or
register task2636 outputs.

The frozen task2625 evaluation records use a positional slot key
`[rule, seed, family, learner_color, endpoint]`; its query/game auditor therefore
cannot be applied unchanged to task2636's named
`[candidate_index, family, learner_color, endpoint]` universe. The new audit
must verify the candidate-index mapping once, then use the structured key for
slot/query grouping and require the repeated candidate seed to match the
indexed root. The inspected compressed task2625 query rows also carry
`record_before`, `record_after`, `actor`, `ply`, `nodes`, `requested_nodes`,
`complete` and `weights`, which is the useful history-replay substrate already
reflected in the task2636 contract.

Then the auditor should run `audit_completed_rows`, `validate_result_receipt`,
and one reused `FrozenSlotReplayContext` over every closed slot, grouping query
rows by exact slot key. It must compare byte hashes for the slot/query files to
the final receipt, keep the full 1,024-slot complement and 512-pair bounds, and
emit separate counts for actual terminal, completed UNKNOWN and missing. A
`NO_FINAL_RECEIPT` recovery path must verify only the start receipt and complete
JSONL prefix, preserve any truncated suffix, and make no result claim or resume.

## Why implementation remains gated

The task2625 result/audit/binding records demonstrate the source model for this
interface, but task2636 has no candidate-index runner, model snapshot schema,
training audit, write-once registration, evaluation binding, or rows. Defining
the above is not a substitute for validating those producer outputs. The current
657.368-second prep/audit/reporting reserve is allocated to remaining replay,
analysis and reporting; no measured estimate covers implementation and tests for
this integrated entry point. Do not create `run-v1` or claim the 66.70-minute
projection is all-in. Preserve the 6,600-second lifetime cap, 110-minute hard
cap and under-120-minute Chat threshold; if an updated expected run reaches two
hours, obtain the existing mailbox assessment before registration or launch.

## Decision

The smallest useful next implementation is a read-only orchestration layer over
the three tested primitives, after a candidate-index training-result/audit
schema is fixed. It should first be validated on empty/missing-only and synthetic
malformed receipts, then on a legal UNKNOWN slot; a real scoring-terminal test
must come from a preserved legal source record, not a new evaluation sample.
Current evidence remains design/preflight only. No registration, training,
search, evaluation or result rows were created.

The reusable source context's measured smoke cost was 31.7 ms to read/hash the
6,962,023-byte pool and source index, 34.9 ms for first candidate compilation
plus one query replay, and 24.0 ms median for ten cached one-query replays.
These timings cover one root and one legal action only; they cannot be scaled to
multi-query slots or used to close the all-in estimate. Receipt:
`results/dev_aux/task2636/replay-context-cost-smoke.json`.
