# GenericChess F83-R2 Durable Provenance Contract Finalization

## Scope

This zero-compute corrective finalizes the executable and testable durable
contract for F83-R1. It does not rerun teacher probes, resample roots, train,
fit a candidate, run Arena, change production semantics, or invoke Heavy.

R2 baseline: `7252994d78810b63f92f91564dddc206dd7fda94`.

## Corrections

- The immutable historical probe source is fixed to the published baseline
  artifact SHA `3b05ff6d999928f97906b4eedae611b5c15b50ae06786cbb674cfaef3063e2ab`.
  Re-running the corrective command cannot replace that pointer with the
  current v2 artifact hash.
- F62 tests now call tracked
  `scripts/f62_learned_champion_repeatability.py::_fresh_records(compiled,
  smoke=False)`, verify 96 unique records, the 48/24/24 split, both seeds,
  the 32x3 structure, and the exact records SHA.
- Root tests now replay all 54 saved histories, verify ongoing status and
  canonical position identities, recompute root-set identity, and recompute
  disjointness against F62, F75, F77, F78/F80, and F81 source corpora.
- The ordinary F83 entry point now reports the v2
  `lower_bound_for_48_acquisition` field and has no stale v1 estimate access.

## Verification

The F82/F83 suites pass (`7 passed`). No `.generic_chess_flow` runtime
dependency was introduced into the durable F83 implementation or artifacts.

Final checkpoint: `c8b56d86abc3ca412bcbfa0b992601b9d3401087`.

F83 remains classified as
`C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_LOWER_BOUND_ONLY`.
