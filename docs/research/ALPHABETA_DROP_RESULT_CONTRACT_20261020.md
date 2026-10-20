# AlphaBeta drop-result contracts

## Question

Do the public AlphaBeta paths preserve both legacy `DropMove` and generated
semantic `SemanticDropMove` identity/state effects through the PV and session
record boundary?

## Evidence and result

The legacy route uses an actually reachable sequence: a Knight captures an
opponent pawn, the opponent moves, and the original side searches with that
pawn in hand. A fixed leaf evaluator selects a legal pawn drop; the test checks
the PV head, hand decrement, new board piece, submission and exact serialized
replay.

The mixed semantic fixture now asks AlphaBeta to choose its generated
`SemanticDropMove` after an existing promotion/capture-to-hand/advance sequence.
The default optional Native legality provider is active; the returned action
retains the `A0` base type and generated `drop_A0` pattern suffix, appears at the
PV head, consumes the correct hand entry, and survives submission and exact
record replay. Search remains AlphaBeta; this does not test or claim Native
iterative search support for every drop-capable rule.

Focused results: `tests/product/test_ai_search.py`,
`test_promotion.py` and `test_drops.py` — 58 passed. The F24C focused regression
passes after correcting its expected identifier to account for the semantic
compiler's generated `sem_12_` prefix; the first version of that assertion
failed on the test's over-specific ID expectation, not on search behavior.
No runtime/drop-generation change and no full-domain claim follow.
