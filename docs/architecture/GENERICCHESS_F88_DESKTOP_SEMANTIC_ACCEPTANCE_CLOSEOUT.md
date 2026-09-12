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
- reset through the existing `MainWindow` restart action, including UI
  last-move markers, history, board, side-to-move, and position identity.

Semantic board/drop action shapes are projected through the existing action
helpers; no second legality or transition implementation was added. Promotion
and Shogi drop product functionality were not expanded because neither is
required to establish this slice.

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
