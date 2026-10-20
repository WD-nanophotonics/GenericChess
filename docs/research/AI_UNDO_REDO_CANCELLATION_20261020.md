# Cancel superseded AI searches on UI Undo/Redo — 2026-10-20

## Decision question

When the GUI mutates the current session with Undo or Redo during an AI turn,
does it stop the now-obsolete search as well as reject its eventual result?

## Reachable failure and repair

`MainWindow` binds Ctrl+Z/Ctrl+Y and the menu actions directly to
`UIController.undo()`/`redo()`; their enablement depends on available history,
not on `ai_thinking`. Before the repair both methods advanced the AI generation,
so `finish_ai_move()` would reject a late snapshot, but neither canceled the
worker token. Undo cleared the controller's thinking/token references without
cancellation; Redo left the thinking state live. This was bounded wasted work
and inconsistent controller state, not a reproduced illegal commit or board
corruption.

Two new tests failed before the fix exactly because the captured token remained
uncanceled after each supported mutation. The controller now cancels the owned
token and clears the thinking/token state in both methods before rebuilding the
session. Generation/root checks remain the independent late-result guard.

## Validation and limits

- Both focused regressions pass after the repair and assert restored ply/state,
  cancellation, cleared thinking state, and rejection of the late result.
- The complete affected five-module suite passed from a fresh ignored basetemp:
  `test_ai_match.py`, `test_ui_app.py`, `test_f27_declaration_integration.py`,
  `test_benchmark.py`, and `test_ai_search.py`. Full output is retained at
  `.local_agent/research/20261020-ai-lifecycle-final.log`.
- A bounded offscreen Qt probe used the actual MainWindow Undo/Redo actions and
  a cooperative test player. Undo+Redo canceled the old worker token; its
  completion was discarded and exactly one replacement worker started for the
  restored AI turn. Window close canceled the replacement worker. The probe
  output was `calls=2, both_tokens_cancelled=true, ply_after_redo=1`.
- Restart, ruleset load and record load GUI entry points already use the
  window-owned cancellation/wait path before replacing the controller session.
  No external production caller bypassing these UI guards was found. A direct
  programmatic concurrent call to lower-level controller mutators is outside
  the current contract.

The Qt probe's first two invocations stopped at test-harness imports before
creating a window; the import path was corrected and the successful run above
is the only run that reached the scenario. This result does not measure real
AlphaBeta cancellation latency, guarantee worker shutdown for noncooperative
backends, or change the generic-search price evaluation. No price, search
policy, benchmark eligibility or backend default changed.

## PassAction benchmark caller coverage

A separate test-only caller check covers the coordinate-free generated action.
A bounded depth-1 AlphaBeta request on the pass-enabled fixture returns a real,
nonfallback `PassAction`; `play_game` receives that captured search result and
submits it through `GameSession`, recording exactly one `pass` event at ply 1.
The configured one-ply cap leaves the outcome unresolved and the row eligible.
An initial attempt let the runner re-search under its distinct iterative
node-budget policy and selected `b1-b4`; that did not test the intended fixed
decision-consumer contract. The corrected harness isolates the already searched
action. All 48 tests in `tests/product/test_benchmark.py` pass. This adds no
product change and establishes neither a PassAction search-policy guarantee
under benchmark limits nor strength/price evidence.

The neighboring `SemanticBoardMove`/`SemanticDropMove` variants share the same
runner path: it stringifies the action for the event and submits the original
`Action` object through `GameSession`, with no action-type dispatch. The focused
existing mixed-mechanic test also passed: AlphaBeta generates a semantic drop
after capture, the session applies it and serialized record replay preserves
the resulting state. A second action-specific paired-game fixture would not
isolate a different consumer contract, so no additional test/API change follows.
