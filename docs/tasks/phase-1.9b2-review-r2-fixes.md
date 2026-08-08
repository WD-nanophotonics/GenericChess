# Task — Phase 1.9B-2 Independent Review R2 Fixes

Reviewed implementation: `3f3affd0760a1bdee663885ca1050c0b7c942860`

This is a correction pass, not Phase 1.9B-3.

Read R2 audit, ADR-015, all R0/R1 specs, every `tests/specification/**`, then
actual production source.

## Required order

1. Lossless semantic public action identity + exact geometry binding.
2. One pre-action binding context for TypeRef/SquareRef/guard/effect.
3. Canonical aux keys/state/defaults + semantic repetition identity.
4. Correct PER_OWNER expiration + AUX_SLOT_SQUARE.
5. Semantic ruleset-mismatch checks.
6. Close `legal_successors` / public dispatch holes.
7. Pseudo-attack exact type/geometry + S1 guards + attacker perspective.
8. Harden remove/move/shift/place semantics.
9. Update legacy capture lowering and EP fixture victim bindings.
10. Expand focused/differential tests.
11. Full suite + freeze audit.

## Allowed

- `generic_chess/core/**`
- `generic_chess/rules/**`
- focused non-spec tests/docs
- minimal Core action serialization changes.

Session/GameRecord semantic schema expansion is not required. Existing Session
serialization must explicitly reject a semantic action rather than silently
reinterpret it.

## Frozen

No semantic implementation changes to Native, search/evaluator, learner, or
UI/Session legality ownership. Do not implement S4.

R0/R1/R2 specification is frozen.

## Required regression

- semantic action dict round-trip;
- duplicate visible coordinates with different pattern/effects;
- same target via multiple geometry paths;
- semantic key default canonicalization;
- mixed GLOBAL/PER_OWNER;
- PER_OWNER ephemeral lifetime;
- AUX_SLOT_SQUARE scope/default;
- ruleset mismatch;
- semantic legal_successors;
- conditional capture pseudo-attack;
- attacker-relative blocker owner filter;
- action-relative effect TypeRefs;
- EP missing/friendly/wrong-type victim;
- compound destination occupancy;
- existing legacy legal/transition/terminal/key differential.

## Final verdict

Only:
- `PYTHON_S0_S3_REFERENCE_EXECUTOR_READY`
- `REFERENCE_EXECUTOR_REQUIRES_REVISION`
- `SPECIFICATION_BLOCKER`

Do not merge master in this task.
