# GenericChess F87A-R6 Closeout

- Baseline: `2d7db69c470ec7e56ec595799b0bef198715b2d3`
- Scope: bounded termination-control evidence only; no R5 full-game fallback rerun.
- Runtime: production semantic runtime through `initial_state` and `apply_action`.
- Controls: deterministic material-capture greedy, deterministic complete-root material search, and deterministic complete-root terminal-aware search.
- Budget: two pairs per control, 128 plies, 64 root actions per ply, and at most 4 canonical opponent replies per root action; incomplete root sets terminate as `SEARCH_BUDGET_CENSORED` and never fall back.
- Compute: 24 games total (12 per ruleset), 68,516 search nodes, zero Arena games, zero training steps, zero Heavy jobs.

## Results

| Ruleset | Pure sequences | Control-distinct sequences | Search coverage | Budget censored | Semantic terminal | Viability |
| --- | ---: | ---: | --- | ---: | --- | --- |
| Built-in Western Chess | 3 | 3 | 512/512 (material + terminal search) | 0 | all three controls: 4 `CENSORED` each | `DEFER` |
| Built-in Standard Shogi | 2 | 2 | 88/88 (material + terminal search) | 0 | all three controls: 4 `repetition` each | `PASS` |

The move-sequence digest contains only actor/action pairs. The execution-trace digest remains separate and includes instrumentation. Terminal utility is reported separately from censorship and is null for censored trajectories.

## Evidence

- Manifest SHA-256: `41cc60f8d35278370381a8d50bf92cfcf082d972b2be0952fcacd09782318eed`
- Summary SHA-256: `f33ed4fe0a720098730365ddb64bec6eb1d5e6b9635307a5440ea0f5c461e63`
- Reports SHA-256: `87dcc32070fd1bf7687ccf218be94e03efe9dc07e8f873ca3a0bd194ba3085b0`

The R6 checkpoint does not authorize promotion. The added terminal-aware bounded control also remained CENSORED on Western despite complete root-set coverage and zero budget censorship, so Western termination remains deferred. Standard Shogi passed through repetition with complete root-set coverage.

The global game count is derived from the per-ruleset dynamic reports: 24 games total, 12 for each ruleset. The accounting regression requires `summary.compute_usage.new_games` to equal that report-derived sum.

## Framework correction

The supervisor-resolution JSON payload is now passed through `_console_safe` before stdout emission, preventing Unicode detail text from failing on legacy Windows encodings. A focused regression test covers UTF-8 detail text under simulated `cp1252` stdout.

Resolved escalation dossiers are immutable: a repeated recovery event with the same escalation identity returns the existing dossier instead of reopening it as `PENDING` and re-freezing the worker.
