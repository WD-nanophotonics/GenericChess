# F94 R6 Layer-D Authority Refresh Result Closeout

The single Supervisor-approved v4 Heavy invocation completed successfully.
No parameter, lane, sample, path, or SHA was changed, and no second Heavy run
was started.

## Immutable execution binding

- Approved plan: `f94-r6-layer-d-authority-refresh-20260913-v4`
- Plan SHA256: `f33e3448c886196f10779dab72dd4ba0ee7d3da3fdbdcbd49b5c0bc16345124c`
- Canonical resource-envelope digest: `2f1f9e6af14815faae8f8833bff7d780a419df313dc15ae7e315b10342edfb57`
- Execution sandbox SHA: `c065e8ea975b809b44dfe1cb599fdce2934024f1`
- PREP byte SHA256: `78b935c3cb5391851bd8a8a574d25ac69714f030a49a01e6006c1d7d8133b8ba`
- Protocol source SHA: `5713b0b6041116d1e03400f0c8db0e3f4d02870a`
- Result artifact: `.generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json`
- Result artifact SHA256: `a3008d1cc0150b82bc1682e7873a9cbe6c27232f359e57479689b486c956e4fe`

## Exact accounting and classifier outcome

The executor returned `R6_RESULT_COMPLETE` with exactly:

- 18 Arena invocations
- 108 complete role-swapped pairs
- 216 games
- 216 action traces

Both frozen controls completed all three tapes and all three fixed matchups.
The pre-registered classifier returned `DEFER_NONMONOTONE_OR_UNCERTAIN` for
`western_chess_qualification_control_v1` and `standard_shogi`, yielding
`DEFER_CONTROL_NOT_READY`. This is the measured fixed-sample outcome; no
historical observations were pooled, no production ruleset was changed, and
the result does not authorize promotion.

Resumable progress contained complete pair checkpoints for all 18 identity-
bound control/matchup/tape directories. The result was produced only after
all six pairs per invocation passed replay, identity, telemetry, trace, and
accounting validation.

## Verification

The approved Heavy command exited 0. The result artifact was inspected for
status, exact accounting, and both control classifications. Runtime progress,
raw result JSON, and Heavy state remain ignored and are not part of Git.
