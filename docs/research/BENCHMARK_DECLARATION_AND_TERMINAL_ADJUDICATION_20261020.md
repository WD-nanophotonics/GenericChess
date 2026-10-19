# Benchmark declaration and terminal adjudication — 2026-10-20

## Question and reproduced behavior

Does the public paired benchmark preserve every terminal decision returned by
`AlphaBetaPlayer` on a ruleset with session-level declarations?

On the existing `_claim_ruleset()` fixture at its initial position,
`GameSession.available_declarations()` returns `opaque_claim=WIN` with weighted
score 10. `AlphaBetaPlayer.choose_action()` returns
`choice_kind="DECLARATION"`, `action=None`, and the matching assessment. Before
the repair, `benchmark.runner.play_game()` treated `action=None` as a failed
game at ply 0; it did not call `GameSession.declare()`. This is a caller/result
handling defect, not a search error.

## Repair and checks

The benchmark now routes declaration choices through the authoritative
`GameSession.declare()` transition, verifies its result against the assessment,
and records a declaration event without incrementing the action ply. A
winner-bearing declaration maps to candidate win/loss by the actual winner.
RESTART/no-contest declarations without a winner remain `unresolved` in this
single-game runner; they are neither failed games nor fabricated draws.

The terminal outcome mapper now handles all current `SessionStatus` values:
winner-bearing checkmate, stalemate, perpetual-check, rule-loss and declaration
map to win/loss; stalemate, repetition, max-ply, action-class and no-progress
draws map to `rule_draw`; resignation follows its resigning side; ongoing,
no-contest and winnerless restart/no-contest declarations remain unresolved.

Regression coverage verifies both candidate colors for a root WIN declaration,
a selected RESTART declaration, every current terminal status, and a complete
four-ply semantic no-progress cycle replayed through the benchmark opening.
Validation:

```text
pytest -q -p no:cacheprovider tests/product/test_benchmark.py \
  tests/product/test_f27_declaration_integration.py \
  tests/product/test_no_progress_search_context.py
63 passed
```

## Scope boundary

This repairs the backend research benchmark caller and terminal accounting. It
does not change price/evaluator/search defaults or establish utility/strength.
`PythonSearchBackend` forwards the full decision unchanged. A separate
source-only UI review found `UIController.finish_ai_move()` currently commits
only a non-null action, while the UI can load arbitrary `RuleSet` inputs; a
declaration-capable UI rule can therefore leave the session ongoing after a
declaration choice. That UI integration path was not modified or validated in
this backend change, and this report does not claim UI declaration support.
