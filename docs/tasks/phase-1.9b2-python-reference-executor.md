# Task: Phase 1.9B-2 — Python S0-S3 Reference Executor

Baseline: `6d6ddd4f00d059e6647a37664044a7030a4f802d`

Read first:
- `docs/rule_semantics_architecture.md`
- `docs/rule_semantics_ir_executable_contract.md`
- `docs/audits/2026-08-phase-1.9b2-pre-executor-audit.md`
- `docs/architecture/ADR-013-semantic-executor-support-and-identity.md`
- `tests/specification/**`

## Goal

Make Python Core the first executable reference implementation of semantic IR S0-S3, while preserving all legacy behavior and keeping Native/Search/Learner frozen.

## Allowed production scope

- `generic_chess/rules/**` only as needed to complete generic support data/capabilities and fix source-confirmed contract defects.
- `generic_chess/core/**` for semantic runtime action/state/executor integration.
- normal non-spec tests and docs required by the implementation.

## Forbidden scope

- `generic_chess/_native/**`
- `generic_chess/native/**`
- search algorithm/evaluator changes in `generic_chess/ai/**`
- learning algorithm semantics (`tdleaf.py`, `features.py`, `selfplay.py`, etc.)
- UI/Session-owned legality state
- S4 `no_legal_reply` execution / Uchifuzume implementation
- game-name execution branches (`if chess`, `if shogi`, `if xiangqi`, `if cannon`, etc.)

## Frozen specification

Files under `tests/specification/**` plus ADR-013 and the pre-executor audit are specification. Do not weaken or rewrite their semantics to make the implementation pass. If a genuine contradiction is found, stop with `SPECIFICATION_BLOCKER` and report the exact conflict.

## Required implementation order

1. Complete the semantic compiled support payload and fix anchor/owner-relative lowering defects.
2. Add canonical aux state to `Position`, serialization and position identity without changing legacy keys.
3. Add runtime semantic action identity/binding (`pattern_id` must distinguish otherwise identical source/target actions).
4. Implement pure square/type/owner/slot resolution helpers.
5. Implement S0 candidate generation and target/path filtering.
6. Implement S1 state/slot guards.
7. Implement semantic pseudo-attack independently of full legal-action recursion, using the same compiled geometry/predicates.
8. Implement bounded effects + aux lifecycle + transition triggers.
9. Implement S3 invariants / trial transition.
10. Integrate terminal/repetition through the public Core path without introducing a second parallel game engine.
11. Enable `new_ir_core_executable=True` only for S0-S3-capable semantic rulesets; S4 remains fail-closed.

## Required behavioral stress tests

- Cannon: 0-screen quiet yes, 0-screen capture no, 1-screen capture yes, 2-screen capture no; attack semantics match conditional capture geometry.
- Castling: normal anchor moves preserved; exact two-square compound move; path/source/transit/destination safety; per-owner rights; rights permanently lost after watched-piece leave/removal; replacement piece does not restore right.
- En passant: empty landing square; off-target victim; token equals landing square; one-opponent-turn lifetime; both diagonal directions and both owners.
- Nifu: only same-owner, same-file, same-base-type, unpromoted board piece blocks drop; promoted/different type/different file do not.
- Legacy differential: representative legacy rulesets produce identical legal actions, transitions, terminal outcomes and historical position keys.

## Deliverables

- production implementation;
- passing frozen specification tests;
- focused unit/regression tests;
- full pytest;
- explicit freeze audit for Native/Search/Learner;
- report Observed / Inferred / Not Established;
- push implementation branch only after all gates pass.
