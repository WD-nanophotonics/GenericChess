# Task: Phase 1.9B-2 Independent Review R1 Fixes

Implementation under review: `6a7bd95`

Do not start Phase 1.9B-3. Do not merge master.

Read:
1. `docs/audits/2026-08-phase-1.9b2-independent-review-r1.md`
2. `docs/architecture/ADR-014-semantic-runtime-binding-and-event-semantics.md`
3. original Phase 1.9B-2 task/audit/ADR
4. all `tests/specification/**`

## Required fix order

1. Fix logical auxiliary scope, including semantic keying.
2. Replace final-board trigger inference with an explicit bound transition event
   trace; verify opponent capture invalidation.
3. Fix action-relative TypeRef binding.
4. Enforce anchor non-capturability while preserving pseudo-attack.
5. Make S4/runtime capability rejection explicit and fail-closed.
6. Make public semantic application non-forgeable.
7. Integrate semantic execution additively through existing public Core
   initial-state/legal-action/apply/terminal lifecycle.
8. Repair forced-promotion parity.
9. Close multi-type actor/geometry/drop binding.
10. Implement lattice `PATH_BETWEEN`.
11. For `location="hand"`, either implement a separately documented complete
    contract or fail-closed; R1 strongly prefers fail-closed rather than
    expanding the DSL in this correction.
12. Add stronger legacy differential tests for actions, child transitions,
    terminal outcomes and historical keys.

## Required public Core properties

For both legacy and semantic compiled rulesets:
- public initial-state construction works;
- public legal-action query works;
- public apply validates action membership;
- child GameState increments ply;
- repetition uses the correct position identity;
- terminal status is constructed by the Core lifecycle.

Do not make Session/UI/Search own semantic legality.

## Required regression coverage beyond frozen R1 tests

- both owners' castling rights remain independent;
- ordinary capture of watched partner square permanently clears only the
  victim owner's right;
- replacement piece cannot restore the right;
- state guard `ACTION_BASE` ignores different-type pieces;
- anchor attackable/not capturable;
- forged action rejected;
- S4 engine/public path rejected;
- forced-promotion/no-alive-target matches legacy;
- multi-type legacy-atom pattern has no cross-product;
- public Core transition + terminal differential;
- duplicate-generation audit: do not hide defects by converting legal actions
  to sets before comparing cardinality/canonical identity.

## Frozen areas

No changes to:
- `generic_chess/_native/**`
- `generic_chess/native/**`
- search/evaluation in `generic_chess/ai/**`
- learner semantics
- Session/UI legality ownership

R0 and R1 specification files may only be copied from the provided packages.
Do not weaken them.

## Verdict

Allowed final verdicts:
- `PYTHON_S0_S3_REFERENCE_EXECUTOR_READY`
- `REFERENCE_EXECUTOR_REQUIRES_REVISION`
- `SPECIFICATION_BLOCKER`
