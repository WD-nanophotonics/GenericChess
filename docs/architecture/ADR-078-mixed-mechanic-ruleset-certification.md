# ADR-078: mixed-mechanic victim-specific capture disposition

## Status

F24C passes with zero production-code changes. The next boundary is
`F24D_WESTERN_CHESS_RULESET_PERFT_CERTIFICATION`; `master` remains locked.

## Decision

Use the existing semantic DSL to express capture disposition by the captured
piece family. Each capture pattern has the same actor/geometry contract but a
target-local `RuleStateGuard`: opponent ownership, exact target square, and
`compare_field=base` against an opaque family base type. The effect then uses
`capture_to_hand` for family A and `remove_from_game` for families B and C.
Promoted victims therefore match their base family without a new selector or
effect primitive. Capturer family does not select disposition.

The certification fixture is
`tests/fixtures/f24c_mixed_mechanic_certification.json`, and its executable
tests are `tests/test_f24c_mixed_mechanic_certification.py`. The ruleset uses
neutral IDs A0/A1, B0/B1, C0, and H0; no game-name or traditional-piece-name
branch is involved.

## Evidence

The cross-capturer matrix proves A0 and promoted A1 victims enter the hand as
base A0 for A0, B0, and C0 capturers. B0/B1 and C0 victims are removed for all
capturers. A0 is the only droppable family; B/C imported inventory has no
semantic drop action. A0->A1 and B0->B1 promotion pass, C0 is nonpromotable,
and the C ray capture is legal only with exactly one blocker.

One simultaneous root contains active hand capture, remove capture, C path
capture, A drop, A promotion, and B promotion. Public semantic identity and
binding uniqueness survive. RuleSet round-trip/fingerprint, F24B qsearch and
ordering, SearchPathRuntime push/pop, and invalid-action rollback pass. A
deterministic type-ID rename preserves action shape and disposition. The mixed
ruleset's exact production Native provider attempt is active; historical
Standard Shogi Native/full-suite failures remain the known F13/F14/F21 enum
and provider failures recorded in the fixture.

## Scope and next boundary

Production diff is empty. No semantic schema/compiler/executor, search,
evaluator, runtime, workflow, or governance changes were made for F24C. The
next boundary is `F24D_WESTERN_CHESS_RULESET_PERFT_CERTIFICATION`.
