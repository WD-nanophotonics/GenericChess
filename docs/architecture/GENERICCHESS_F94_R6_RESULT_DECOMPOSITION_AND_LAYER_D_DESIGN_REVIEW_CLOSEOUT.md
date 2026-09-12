# F94 R6 Result Decomposition and Layer-D Design Review

This is a pure descriptive decomposition of the completed R6 result. No
Arena, Heavy, new games, bootstrap seeds, confidence method, or classifier
rule was changed.

## Immutable source and aggregate

- Source result: `.generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json`
- Source result SHA256: `a3008d1cc0150b82bc1682e7873a9cbe6c27232f359e57479689b486c956e4fe`
- Aggregate artifact: `docs/architecture/GENERICCHESS_F94_R6_LAYER_D_AUTHORITY_REFRESH_AGGREGATE_V4.json`
- Aggregate artifact SHA256: `6017f31916aa482fc7d618cca9de1f12e4fdbd4d7490ed1d465656a7cbe79e96`
- Extractor: `scripts/f94_r6_result_aggregate.py`

The aggregate retains all 108 pair scores with tape seed, pair index, score,
and status; each tape's six-pair mean and independently recomputed mean; the
pre-registered bootstrap mean/lower/upper/seed/resamples/sample_count; status
counts; child-depth hits/count/fraction; strongest-vs-weakest horizon
hits/games/fraction; and the frozen matchup/control classifier outputs.

## Descriptive findings (non-authoritative)

The frozen authority result remains `DEFER_CONTROL_NOT_READY`; the aggregate
does not alter that decision. Standard Shogi's 1024-vs-256 matchup is frozen
as `DEFER` because its pair statuses include fallback observations, while its
tape means are 0.625, 0.750, and 0.708333 and its bootstrap lower bound is
0.611111. Its other two matchups are `PASS`.

Western qualification's 1024-vs-256 and 4096-vs-256 matchups are `PASS`. Its
4096-vs-1024 matchup is `DEFER_NONMONOTONE_OR_UNCERTAIN`, with tape means
0.708333, 0.541667, and 0.458333 and bootstrap lower bound 0.472222. The
non-authoritative attribution is `NONMONOTONE` because at least one tape mean
is at or below 0.5. No aggregate field changes the frozen classifier or Layer-D
authority state.

The aggregate records depth-censoring fractions directly from the
identity-bound pair checkpoints and horizon diagnostics for the strongest
matchup. These are descriptive evidence only; runtime timing/NPS fields are
not included.

## Verification

The deterministic extractor was run twice and produced identical JSON. The
focused R6, arena-integrity, and aggregate tests passed (38 tests), including
exact 108-pair retention, per-tape mean recomputation, source-SHA fail-closed
behavior, and descriptive-attribution tests. Runtime result/progress files
remain ignored and were not added to Git.
