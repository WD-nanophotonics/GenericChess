# GenericChess F87A-R6 Closeout

- Baseline: `2d7db69c470ec7e56ec595799b0bef198715b2d3`
- Scope: bounded termination-control evidence only; no R5 full-game fallback rerun.
- Runtime: production semantic runtime through `initial_state` and `apply_action`.
- Controls: deterministic material-capture greedy versus deterministic complete-root material search.
- Budget: two pairs per control, 128 plies, 64 root nodes per ply; incomplete root sets terminate as `SEARCH_BUDGET_CENSORED` and never fall back.
- Compute: 8 games, 14,000 search nodes, zero Arena games, zero training steps, zero Heavy jobs.

## Results

| Ruleset | Pure sequences | Control-distinct sequences | Search coverage | Budget censored | Semantic terminal | Viability |
| --- | ---: | ---: | --- | ---: | --- | --- |
| Built-in Western Chess | 2 | 2 | 512/512 (1.0) | 0 | 4 greedy + 4 search `CENSORED` | `DEFER` |
| Built-in Standard Shogi | 2 | 2 | 88/88 (1.0) | 0 | 4 greedy + 4 search `repetition` | `PASS` |

The move-sequence digest contains only actor/action pairs. The execution-trace digest remains separate and includes instrumentation. Terminal utility is reported separately from censorship and is null for censored trajectories.

## Evidence

- Manifest SHA-256: `e35223987b915cce944f4e17cd1707197833078f4af51d0585048510157d19f2`
- Summary SHA-256: `35b3049cf81dc3e055962a319cb15e7f020c387d3c3c9033753f07156c44f1aa`
- Reports SHA-256: `5cb30684fe18ae3cd253088527c8a16756209b2682314dc7b3734e9c3fc20bca`

The R6 checkpoint does not authorize promotion. Western termination remains deferred because its bounded horizon did not reach a natural semantic terminal; Standard Shogi passed through repetition with complete root-set coverage.

## Framework correction

The supervisor-resolution JSON payload is now passed through `_console_safe` before stdout emission, preventing Unicode detail text from failing on legacy Windows encodings. A focused regression test covers UTF-8 detail text under simulated `cp1252` stdout.
