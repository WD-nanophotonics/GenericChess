# GenericChess F88 desktop semantic acceptance

Work order: `GENERICCHESS-F88-DESKTOP-SEMANTIC-ACCEPTANCE`

## Result

The built-in Western Chess and Standard Shogi rulesets now load through the
production desktop path. `UIController.new_game_from_builtin()` and
`UIController.new_game_from_ruleset()` use the existing
`compile_ruleset_for_execution()` dispatcher, so semantic rulesets reach the
same executable semantic runtime used by the product boundary instead of
being sent to the legacy-only compiler. The New Match dialog exposes both
built-ins through the existing desktop new-game flow.

The deterministic offscreen acceptance covers, for each built-in:

- built-in selection through `NewMatchDialog` and the desktop new-game path;
- piece selection and legal target submission through `square_clicked()`;
- side-to-move, board occupancy, and canonical position identity agreement
  between the semantic session, `BoardViewModel`, and rendered occupancy;
- rejection of an empty, unavailable target without changing semantic state;
- an existing Standard Shogi capture sequence followed by the real
  `PlayerBar` hand-button interaction and semantic drop target click;
- drop hand-count, history-action, position-identity, and rendered-occupancy
  agreement;
- reset through the existing `MainWindow` restart action, including UI
  last-move markers (explicitly all cleared), history, board, side-to-move,
  and position identity.

Semantic board/drop action shapes are projected through the existing action
helpers; no second legality or transition implementation was added. The
existing drop entry point was tested without expanding product functionality.

## Verification

Focused command:

```text
.venv\\Scripts\\python.exe -m pytest -q tests/test_f88_desktop_semantic_acceptance.py
```

Additional verification:

```text
.venv\\Scripts\\python.exe -m pytest -q tests/test_ui_controller.py tests/test_ui_app.py tests/test_f88_desktop_semantic_acceptance.py
.venv\\Scripts\\python.exe -m pytest -q tests/test_western_chess_product.py tests/test_standard_shogi_product.py tests/test_f88_desktop_semantic_acceptance.py
```

No Arena, training, external engine, Heavy job, or F87A termination
discovery was run.

## F88-R1 corrective addendum

The corrective acceptance now drives a deterministic, promotion-free Standard
Shogi sequence through production `square_clicked()` actions, captures a
non-pawn piece, makes a legal reply, and selects the existing side-0
`PlayerBar.hand_buttons()` control. It asserts that the resulting interaction
contains a production `SemanticDropMove`, then verifies the exact drop in
history, hand decrement, side/position identity change, `BoardViewModel`
occupancy, and rendered occupancy. The restart path explicitly asserts that
all `is_last_move_from` and `is_last_move_to` markers are cleared.

F88-R1 focused verification passed:

```text
.venv\\Scripts\\python.exe -m pytest -q tests/test_f88_desktop_semantic_acceptance.py
```
