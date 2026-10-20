# Search backend production callers — 2026-10-20

## Question

Does `SearchBackend` currently define the production replacement seam for the
UI or benchmark paths, so generated-rule backend work should target it now?

## Bounded source audit

The only direct `PythonSearchBackend` / `SearchBackend` constructions and calls
under `generic_chess/` and `tests/` are in two product tests
(`test_generic_pass_action.py` and `test_search_tuning.py`). No production caller
constructs the adapter or accepts `SearchBackend`.

The UI worker in `generic_chess/ui/main_window.py::_AiThread.run` calls
`Player.choose_action(session, limits, cancel_token=..., progress_callback=...)`
directly. `UIController.capture_ai_search` builds a `SearchSnapshot`, but the
worker unwraps it and invokes the player's method rather than a backend. The
controller also has a runner-taking helper used by product tests; the MainWindow
production path does not route through it. The benchmark game loop in
`generic_chess/ai/benchmark/runner.py::play_game` calls
`player.choose_action(session, limits)` directly and then interprets
`PlayerDecision` metadata for fallback/timing and outcome accounting. Native
readiness diagnostics separately call `AlphaBetaPlayer` with an
`AuditRecorder`; that instrumentation path is also not a `SearchBackend`
consumer.

`SearchBackend.search` instead receives a `SearchSnapshot` and cancellation
token, with no progress callback. `PythonSearchBackend` adapts this to the
player protocol by unwrapping `snapshot.session` and `snapshot.limits`. The
module's former claim that UI and benchmark callers already depend only on this
boundary was inaccurate. The source-only audit found no runtime mismatch: the
adapter is not currently on those production paths.

## Decision consequence

For current generated-rule work, the UI worker and benchmark game loop use the
`Player.choose_action` protocol; `SearchBackend` is an experimental adapter,
not a live interchange guarantee. Corrected its
module/protocol documentation accordingly. Do not route UI or benchmark code
through a broader adapter or add another API without a concrete alternate
backend that needs it. When that need appears, the integration must preserve
UI progress/cancellation and benchmark decision/fallback metadata, then test a
real production caller. This evidence changes which seam future backend work
must integrate with; it does not show a current search-result defect or prove
that all generated-rule backends are interchangeable.

## Evidence limits

This was a bounded repository call-site audit, not execution of a native
backend or end-to-end UI replacement. Existing adapter product tests remain
unchanged and exercise only the experimental wrapper.
