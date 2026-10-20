# UI AI root-declaration commit — 2026-10-20

## Question

Does the production Python UI caller apply a declaration selected by the AI as
the authoritative terminal result, while preserving board/history and match
clock semantics?

## Evidence and defect

On the custom declaration-capable `_claim_ruleset()` product fixture,
`AlphaBetaPlayer.choose_action()` returns a legal root `WIN` declaration with
`choice_kind="DECLARATION"`, `action=None`, and a rule-derived declaration ID.
Before the fix, the Qt-free production `UIController.finish_ai_move()` rejected
that result because it only committed non-null actions. A direct reproduction
left the same root state and ply count zero, but the session remained ongoing;
the AI side was still required to move and the controller surfaced a commit
error. Since `MainWindow._on_ai_finished()` starts another AI search whenever
the game still requires an AI move, repeatedly receiving the same declaration
could loop without changing the game.

This is a live `PlayerDecision` consumer mismatch, not a search-scoring or
declaration-assessment defect. `GameSession.declare()` is already the authority:
it validates the declaration against the current rules/state and records a
terminal declaration without changing the board or action history.

## Change

`UIController.finish_ai_move()` now routes only an explicitly selected
declaration with no accompanying action through a private declaration-commit
path. That path calls `GameSession.declare()` using the supplied ID, so unknown
IDs fail under the session's existing rules. Successful declarations finish
the mover's clock turn and pause a terminal match clock; they add no synthetic
action. Invalid or malformed declaration results retain the ongoing session,
surface an error, and stop automatic AI retries until the user resumes them.
Existing cancellation, stale-snapshot, normal action submission, and
`PlayerDecision` stubs lacking the optional `choice_kind` metadata retain their
previous behavior.

## Verification and limits

The product regression runs the actual AlphaBeta player through the controller
and confirms the `WIN` declaration becomes the session result, leaves the
authoritative `GameState` unchanged, records the declaration, requires no next
AI turn, and pauses the clock. Assessor-derived `LOSS`, `RESTART`, and
`NO_CONTEST` decisions also pass through the controller and preserve the
authoritative winner/status; the normal AI's actual root choice remains the
WIN case. A separate caller input with an unavailable declaration ID checks
fail-closed behavior plus retry suppression. The selected product modules
`test_ai_match.py`, `test_ui_controller.py`, `test_ui_lifecycle.py`,
`test_ui_app.py`, and `test_generic_declaration_semantics.py` passed together.

The actual AlphaBeta fixture exercises one rule-derived root `WIN`; the other
three supported outcomes are tested as assessor-derived caller decisions, not
as independent AI search choices. This does not establish behavior for every
possible rule set. `GameSession` remains the authority for every outcome. No
UI Test branch/app, search policy, benchmark, alternate backend API,
DEV_AUX/DEEPSEEK_AUX source, or auxiliary computation was changed or used.
