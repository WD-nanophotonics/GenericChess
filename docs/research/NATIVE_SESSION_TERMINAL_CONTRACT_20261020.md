# Native session terminal contract — 2026-10-20

## Question and scope

Does the public persistent `NativeSearchEngine` honor session-level terminal
results created by declaration, when the underlying `GameState` remains ongoing?
This is a search-interface correctness check, not a strength or price claim.

## Reproduction

Using the existing finished-session fixture, `Session.declare("done")` leaves the
Core state-level terminal status ongoing but makes `GameSession.legal_actions()`
empty. Before the fix, `AlphaBetaPlayer.choose_action` returned no action, the
terminal sentinel, zero completed depth and zero nodes. `NativeSearchEngine`
instead searched the still-ongoing state and returned `a4-a3` at depth 2 after
22 nodes. That action could not be submitted to the ended session.

## Minimal correction and validation

`NativeSearchEngine.search` now recognizes both session-level
`RESIGNATION` and `DECLARATION` results before packing or entering the native
kernel. It returns no action/PV, zero work and completed depth, and a score with
the same winner/side-to-move sign convention as Core; neutral results remain 0.
A regression matrix checks all five fixture outcomes (resignation, win, loss,
restart and no-contest), both owners, and direct plus record-replayed sessions.
The existing checkmate-root control remains covered. The focused cases passed
11 tests; the complete `test_native_iterative_search.py` module passed 14 tests.

A bounded call-site audit found arena and self-play searches guarded by an
ongoing-session loop and Core legal-action check; teacher diagnostics filter out
terminal sessions. No caller rewrite was needed.

`SemanticSearchEngine` has a separate terminal early return with no action and
zero score. Its result type expressly defines score as a search estimate that
does not certify a terminal outcome; the zero is therefore not an alternative
adjudication. This change leaves that API untouched.

## Limits and consequence

The fix aligns the experimental persistent Native interface with Core for
session-level declaration/resignation terminals. It does not make a claim about
all terminal/search semantics, other backends, or search strength. The issue is
closed for the tested public interface; no general caller or semantic-engine
refactor follows.
