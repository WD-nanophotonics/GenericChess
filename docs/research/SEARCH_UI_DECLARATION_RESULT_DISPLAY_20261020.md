# Display generic terminal results in the production UI — 2026-10-20

## Question

When generic AlphaBeta returns an actionless declaration choice, does the
production UI make the resulting session outcome visible to the player?

## Source finding

`PlayerDecision` represents declarations separately from board actions.
`MainWindow._AiThread` forwards the result to `_on_ai_finished`, which delegates
to `UIController.finish_ai_move`. The controller already validates and commits
the declaration through `GameSession.declare`; the existing AI/controller test
covers the win result and its saved/replayed record. The missing behavior was
presentation: `MainWindow._overlay_lines` had no `declaration` case, so the
game-over overlay hid, and `MovesPanel._result_line` returned an empty string.
The terminal session was committed correctly but its declaration ID/outcome
and winner were absent from the user-facing result.

## Bounded repair

Added localized English, Simplified Chinese and Japanese presentation for
declaration outcomes WIN, LOSS, RESTART and NO_CONTEST, plus the previously
unhandled `PERPETUAL_CHECK`, `NO_CONTEST`, `ACTION_CLASS_DRAW`,
`NO_PROGRESS_DRAW` and `RULE_LOSS` session statuses. The game-over overlay and
moves panel now cover every current terminal `SessionStatus`; winnerless
declarations/no-contest are distinct from draws, decisive outcomes name the
winner, and declaration text retains its rule-authored ID/outcome. Search,
session semantics, action history and rule adjudication are unchanged. This
closes the current result-presenter status map, not every UI control or every
future status an extension might add.

## Validation and limits

The new headless Qt regression reaches an actual declaration terminal and
asserts the overlay and moves panel show the result. Existing
`test_ai_root_declaration_finishes_match_through_session_and_stops_clock`
continues to cover AlphaBeta declaration submission through the controller.
Parameterized presenter tests cover the other declaration outcomes and all five
previously omitted terminal statuses; actual declaration rendering also passes
in English, Simplified Chinese and Japanese. An enum-completeness guard checks
that every current terminal `SessionStatus` has text in both presenters. The
full affected `test_ui_redesign.py` module plus that AI integration test passed 60
tests. A first attempt had a wrong test-fixture import and a Windows
temporary-directory cleanup permission error; both were preserved in command
output, the import was corrected, and the final run used a fresh ignored
basetemp with the supported elevated pytest command. No engine search, games or
training ran.
