# AlphaBeta selects a generated repeated-cycle rule win — 2026-10-20

## Question

Does the public AlphaBeta caller see a one-move semantic action that reaches a
configured repeated-cycle actor loss as an immediate win, rather than only
proving the terminal through Core transition/runtime tests?

## Fixture and method

Reuse the verified 10x9 Xiangqi diagnostic target-cycle fixture in
`tests/product/test_xiangqi_repeated_chase_response_pair.py`. Configure an
actor-0 repeated-cycle target condition, repetition limit 3, and two complete
cycles. Replay the first seven actions into an ongoing `GameSession`; the
closing `SemanticBoardMove` is legal and the eighth action reaches a Core
`RULE_LOSS` with winner 1. Search that parent through public
`AlphaBetaPlayer.choose_action` at depth 1 with a constant evaluation, TT and
ordering disabled, and Native legality disabled.

## Result

The parent has 19 legal actions and remains ongoing. AlphaBeta chooses the exact
closing semantic action and returns a positive `root_immediate_win` result at
depth 0. Parent record equality before/after search is asserted. The focused
regression and the adjacent repeated-cycle identity, AUX-default, F3 corrective,
and root-terminal suites pass.

## Scope and consequence

This closes one generated-rule public caller integration gap: a search-selected
semantic action can exploit the Core's actor-specific repeated-cycle adjudication
as an immediate win. No defect or search implementation change was observed.
It does not establish all repeated-cycle rules, all history-sensitive outcomes,
all AlphaBeta tactical branches, or Native search equivalence. The next route
must be a distinct unfamiliar-rule caller contract; do not expand cycle probes
without a changed premise.
