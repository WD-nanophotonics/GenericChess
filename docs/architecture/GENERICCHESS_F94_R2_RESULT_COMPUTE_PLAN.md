# GenericChess F94-R2 RESULT compute-plan boundary

Status: the frozen RESULT executor is implemented and published; no Arena or
Heavy computation has been launched.

## Published executor

The RESULT entry point is
`scripts/f94_r2_strength_calibration.py --result`. It reads only the frozen
`docs/architecture/GENERICCHESS_F94_R2_STRENGTH_RESPONSE_PREP.json`, rebuilds
the production rulesets/checkpoints/opening corpora, fails closed on any
identity mismatch, short-circuits the A/C boundary candidate, and measures
only the two READY positive candidates through the existing paired Arena.
Focused PREP/protocol tests and a result-free identity audit passed before the
executor checkpoint was published.

## Frozen compute scope

The Chat work order fixes three tapes and three matchups per READY candidate,
with six role-swapped pairs per invocation. That is 9 invocations and 108
games per READY candidate, 18 invocations and 216 games total. The boundary
candidate performs zero Arena work and records
`PREREQUISITE_A_C_NOT_PASS` / Layer-D `DEFER`.

The PREP also freezes `workers=1`; changing it to reduce elapsed time would
change the experiment. The exact versioned resource envelope and compute plan
are generated in ignored runtime state only after this report checkpoint is
published, and must be approved by Chat and the registered Supervisor against
the resulting exact sandbox SHA before Heavy is allowed to start.

## Execution boundary

Until both approvals are bound to the exact plan, envelope, current sandbox
SHA, and command argv, this work remains at the approval boundary. No result
is inferred from prior calibrations, no tuning is allowed, and a cap or
operational failure remains unresolved evidence rather than a draw or loss.
