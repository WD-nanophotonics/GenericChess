# F94 R6 Result Decomposition and Layer-D Design Review

This is a pure descriptive decomposition of the completed R6 result. No
Arena, Heavy, new games, bootstrap seeds, confidence method, or classifier
rule was changed.

## Immutable source and aggregate

- Source result: `.generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json`
- Source result SHA256: `a3008d1cc0150b82bc1682e7873a9cbe6c27232f359e57479689b486c956e4fe`
- Aggregate artifact: `docs/architecture/GENERICCHESS_F94_R6_LAYER_D_AUTHORITY_REFRESH_AGGREGATE_V4.json`
- Aggregate artifact SHA256: `e64f7c617a2b6b10f80c517c3c22a1a9188dbfca98ff78958af44a76515f2905`
- Extractor: `scripts/f94_r6_result_aggregate.py`
- Progress evidence digest: `7d2f0dbb941e49567975f40463341bc4a7adf209781c63756a9e2fe3a8644cdd`

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
non-authoritative attribution is `BOTH`: at least one tape mean is at or below
0.5 and the bootstrap lower bound is also at or below 0.5. No aggregate field
changes the frozen classifier or Layer-D authority state.

The aggregate records depth-censoring fractions directly from exactly one
validated manifest plus six complete pair checkpoints for each of the 18
identity-bound invocations, and horizon diagnostics for the strongest matchup.
It records a deterministic digest over the ordered checkpoint payload hashes,
cross-checks both censoring fractions against the frozen RESULT, and fails
closed on missing, extra, malformed, or identity-mismatched progress. These
are descriptive evidence only; runtime timing/NPS fields are not included.

## Verification

The deterministic extractor was run twice and produced identical JSON. The
focused R6, arena-integrity, and aggregate tests passed (38 tests), including
exact 108-pair retention, per-tape mean recomputation, source-SHA fail-closed
behavior, all four attribution combinations (including the actual Western
`BOTH` case), and progress-evidence fail-closed checks. Runtime result/progress
files remain ignored and were not added to Git.
