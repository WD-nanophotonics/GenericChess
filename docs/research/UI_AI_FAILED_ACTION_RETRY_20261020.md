# UI AI failed-action retry guard — 2026-10-20

## Question

When the live UI consumer rejects an AI-selected action while the match remains
ongoing, does it prevent the same AI turn from automatically restarting?

## Reproduction and impact

The earlier bounded caller probe passed a same-square `BoardMove` through
`UIController.finish_ai_move()`. `GameSession.submit()` rejected it, the board
and action history remained unchanged, and the controller exposed the error.
However, `ai_stop_requested` remained false and `ai_move_needed()` stayed true.
`MainWindow._on_ai_finished()` therefore remained eligible to start the same
AI turn again. Repeated invalid output could become an unbounded retry loop.

A new regression reached that exact live result boundary and first failed on
the retry assertion, confirming the gap rather than only inferring it from
source.

## Change and verification

`UIController.finish_ai_move()` now stops automatic AI retries whenever a
non-cancelled, non-stale decision fails to commit while the session remains
ongoing. Existing action/declaration validation supplies the specific error;
when a decision contains no committable action and no prior error, the
controller supplies a generic visible error. The user can explicitly resume
the AI. Stale and cancelled results retain their existing discard behavior;
successful actions and declarations clear the stop request.

The new regression confirms a rejected same-square move leaves the root state
and history unchanged, preserves the validation error, sets the stop request,
and makes `ai_move_needed()` false. The focused five-module product suite
passed after the fix:
`test_ai_match.py`, `test_ui_controller.py`, `test_ui_lifecycle.py`,
`test_ui_app.py`, and `test_generic_declaration_semantics.py`. The same new
test failed before the code change at the stop-request assertion.

## Limits and adoption

This closes a reproducible retry-control defect at the existing Python UI
caller; it does not change search, legality, declaration semantics, or the
backend API. The reproduction uses one deliberately invalid same-square action,
not an alternate production backend or an all-rule integration proof. No UI
Test branch/app, AUX checkout/computation, or unrelated process was touched.
No new experiment or broader adapter is justified by this result.
