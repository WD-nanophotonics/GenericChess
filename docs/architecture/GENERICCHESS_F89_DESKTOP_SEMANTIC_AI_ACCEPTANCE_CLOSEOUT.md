# GenericChess F89 desktop semantic AI acceptance

## Scope

F89 verifies one real Human-vs-AI reply for each production built-in:
Western Chess and Standard Shogi. The acceptance starts a built-in match
through `MainWindow._apply_new_match()` with a human side and an AI side, makes
the human move through `square_clicked()`, and lets the existing
`_maybe_start_ai()` → `_AiThread` → `AlphaBetaPlayer.choose_action()` path
complete naturally. No stub player or injected runner is used.

The AI budget is deliberately bounded with `ThinkingStrategy.FIXED_NODES`,
`max_nodes=500`, and `max_depth=2`; each ruleset requires only one reply. The
test asserts no AI error, worker idle state, exactly one AI history entry,
semantic action identity against the AI root legal-action set, return to the
human side, changed semantic position identity, and exact agreement between
`BoardViewModel` and rendered occupancy.

## Verification

```text
.venv\\Scripts\\python.exe -m pytest -q tests/test_f89_desktop_semantic_ai_acceptance.py
```

The test passed for both built-ins. No Arena, training, paired-strength gate,
external engine, Heavy job, or F87A/F88 requalification was run.
