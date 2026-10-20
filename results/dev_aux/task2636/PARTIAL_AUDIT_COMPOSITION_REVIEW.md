# task2636 partial audit composition review

## Scope

Read-only review of the current slot schema, final receipt validator, and
`FrozenSlotReplayContext`. No task2636 result rows exist. No search, training,
registration, or evaluation was started.

## Findings

- Within its declared layer, `validate_result_receipt` rejects boolean-as-integer
  counts, missing-key/complement mismatch, orphan queries, duplicate or
  noncontiguous per-slot plies, query totals that disagree with slot closures,
  and an incomplete query followed by another query. The expanded unit case
  confirms that duplicate ply zero is rejected when aggregate counts are made
  self-consistent.
- `FrozenSlotReplayContext` independently binds a slot to the audited frozen
  plan, pool, index, rule bytes, family root, seed and cap, then replays exact
  pre/post histories and recomputes terminal authority. Initial weights are
  tied to the pinned seed-1977 vector; the foe is fixed to all ones.
- No fail-open was demonstrated when these layers are applied to their intended
  scopes. They are not composed by a single whole-result entry point: the caller
  must run structural row auditing, final receipt validation, and one replay
  for every closed slot with externally audited TDLeaf weights.
- Receipt SHA fields are format-checked only. The current validator does not
  prove that registration/training hashes name actual bytes, that the expected
  model weights came from the audited training artifact, or that rows and the
  final receipt were durably written under the stop protocol. Those remain
  pre-registration implementation gates.

## Decision

Keep task2636 unregistered. Next implementation should compose exact source and
model receipt binding with the three existing audit layers, reuse one replay
context for all slots, and add a real scoring-terminal replay fixture plus stop
and durable-write tests. Re-estimate the all-in development/validation/runtime
cost before considering registration; the frozen 6,600-second cap and 120-minute
mailbox-assessment threshold are unchanged. The current 66.70-minute projection
still excludes this engineering cost.

Validation: `results/dev_aux/task2636/test_partial_evaluation_audit.py` — 10
tests passed; `py_compile` passed. The recorded 37 frozen-source hashes still
match. `run-v1` remains absent.
