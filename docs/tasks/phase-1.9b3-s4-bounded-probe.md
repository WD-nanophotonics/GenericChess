# Task: Phase 1.9B-3 — Python Bounded S4 Post-Action Probe

Read first (frozen): ADR-016, ADR-013, ADR-014, ADR-015,
`docs/rule_semantics_ir_design.md` (§13-§17, §22, §31),
`docs/rule_semantics_ir_stress_tests.md` (§5-§6),
`docs/audits/2026-08-phase-1.9b2-pre-executor-audit.md`, and
`tests/specification/**`.

## Goal

Extend the Python reference executor from S0-S3 to S0-S4 by implementing
the bounded post-action probe (`opponent_checked`,
`no_legal_reply(max_stratum=S3)`, `EXISTS_LEGAL_REPLY(stratum<=S3)`) per
ADR-016.  Generic restricted finish (board move/capture) and
uchifuzume-shaped drop restrictions both use the same primitive.

## Frozen semantics (ADR-016)

- truth table in ADR-016 §2 is the only authority;
- exactly-one-level stratification; nested S4 disabled inside the probe
  (Option B); probe never enters S5; probe consumes the full child;
- early exit is a MUST; `opponent_checked` precedes the reply probe;
- no production game-name branching; no IR/schema bump;
- public Core lifecycle and substantive R0-R3 correctness contracts remain
  unchanged (fingerprint/action identity/exact binding/canonical aux/etc.);
  the two phase-local B-2 S4 fail-closed capability assertions explicitly
  superseded by the B-3 transition are retired per
  `docs/audits/2026-08-phase-1.9b3-spec-r2-retire-b2-s4-gate.md`.

## Implementation order (frozen)

1. Audit existing postcondition polarity/lowering (already recorded in
   ADR-016 §1; re-verify against source at implementation time).
2. Define one internal stratified legality entry, e.g.
   `legal_actions(position, max_stratum=S4)` (name not frozen) or an
   equivalent iterator.
3. Make the normal S0-S3 path reusable by the probe (same machinery, S4
   disabled).
4. Implement `opponent_checked` (semantic S2 pseudo-attack on the reply
   side's anchor, child position).
5. Implement `EXISTS_LEGAL_REPLY(S3)` (early-exit existence scan).
6. Implement `no_legal_reply` from the existence scan.
7. Integrate S4 as a post-trial filter in candidate legality.
8. Flip `new_ir_core_executable` for supported S0-S4 rulesets; keep
   unsupported/invalid probes fail-closed.
9. Public Core differential: `legal_actions`/`legal_successors`/
   `apply_action` for S4 actions.
10. Stress regressions (drop + non-drop restricted finish, Option B,
    aux-dependent reply, no-S5, capability).

Do not start from the uchifuzume fixture as a special case.

## Allowed files (Phase 1.9B-3 implementation)

- `generic_chess/core/semantic_executor.py`
- `generic_chess/rules/**` (only if genuinely required)
- focused non-spec tests/docs required by the implementation

## Forbidden files (frozen)

- `generic_chess/_native/**`, `generic_chess/native/**`
- `generic_chess/ai/**`, `generic_chess/learning/**`
- `generic_chess/ui/**`, `generic_chess/session/**`

Session semantic schema stays deferred.  Do not implement S5 or any new
postcondition kind.

## Test gates

- Gate A: R0/R1/R2/R3 substantive correctness specification green after
  the explicit R2 supersession of the two temporary B-2 S4 capability gates;
  those two continuity tests now assert the B-3 supported capability
  transition rather than preserve the historical `False` gate.
- Gate B: `tests/specification/test_phase19b3_s4_bounded_probe.py` green
  (SPEC-01..SPEC-11).
- Gate C: semantic executor focused suite + legacy differential green.
- Gate D: full pytest without new regression (known timing flake and
  pre-existing environment issues reported separately).
- Freeze audit: Native/Search/Learner/UI/Session zero diff.

## Acceptance verdicts

- `PYTHON_S0_S4_REFERENCE_EXECUTOR_READY` only when all gates pass.
- `REFERENCE_EXECUTOR_REQUIRES_REVISION` otherwise.
- `SPECIFICATION_BLOCKER` on a genuine frozen-contract contradiction.
