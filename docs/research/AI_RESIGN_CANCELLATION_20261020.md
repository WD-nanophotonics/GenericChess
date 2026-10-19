# Resignation cancels an active AI search — 2026-10-20

## Finding

The Qt-free `UIController` is the backend boundary used by the GUI. The public
main-window path creates a `CancellationToken`, passes it into
`capture_ai_search`, and starts `_AiThread` with that token. The Resign menu is
enabled for an active game; `MainWindow._resign` calls `UIController.resign`
directly. Before this fix, `resign` mutated the live `GameSession` and advanced
the AI generation, so `finish_ai_move` would reject an eventual stale result,
but the running worker was not asked to stop and `_ai_thinking` remained true
until completion. This wasted the remaining bounded search budget after the
game had ended.

## Change and validation

After a successful resignation the controller now cancels the active token and
clears its thinking flag, in addition to the existing generation invalidation.
The regression test starts an AI turn, captures its worker snapshot, models a
late worker result, resigns, and checks token cancellation, ended state, cleared
thinking state and rejection of that result without another move.

`tests/product/test_ai_match.py`: 20 passed. The deterministic test exercises
the controller contract; it does not benchmark wall-time saved or prove the
worker has synchronously exited. Existing cooperative cancellation and the
main-window thread lifecycle remain authoritative. No search algorithm,
evaluation, rules, UI file, or AI default changed.

## Boundary check

The current GUI's ordinary board/hand interaction handlers reject input while
`ai_thinking`; the timeout path already cancels its token, and restart/load
replace the session and invalidate the worker generation. The Resign menu is
the confirmed active-game path that remained uncancelled and is now covered.
The lower-level `UIController.submit_action` method can still be called directly
by programmatic consumers without the GUI interaction guard; repository
production calls are controller-internal, and this segment does not claim that
arbitrary concurrent direct calls are safe. No new snapshot/deep-copy API was
introduced.
