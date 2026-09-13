# F94 R7 Layer-D preregistration closeout

This is a zero-compute prospective checkpoint. No new Arena, Heavy run, game,
tape, bootstrap, or classifier mutation was performed.

## Immutable checkpoint

- Sandbox commit and `origin/sandbox`: `59b8dcff4197723686b54eee0ef2f86f97ccd733`
- R6 parent remains immutable: `951e49c750f3ac0ad8aa6290786c0529ee1071b9`
- Preregistration: `docs/architecture/GENERICCHESS_F94_R7_PREREGISTRATION_V1.json`
- Preregistration schema: `generic-chess-f94-r7-layer-d-preregistration-v1`
- Master remains unchanged at `e6d6236d31d60373a3afb1e12afcfbe8541bcc67`

## Frozen prospective rules

The preregistration binds `4096_vs_256` as the blocking primary endpoint and
`1024_vs_256` / `4096_vs_1024` as diagnostics. A strict negative reversal is
`pair_score < 0.5` in either diagnostic matchup and blocks; the 0.5 mixed
boundary and uncertainty without strict reversal do not block by themselves.

Fallback strata remain separate: low-budget pre-iteration node fallback is a
weak-search diagnostic; high-budget fallback, operational/abort fallback, and
unclassified or post-iteration fallback block fail-closed.

Fresh prospective tape identities are 9811, 9812, and 9813 in the registered
R7 namespace, excluding all R6 seeds 9801, 9802, and 9803. The result schema
requires identity SHA fields, `(control, tape_seed, pair_index)` response keys,
and complete fallback records. Regression fixtures enumerate endpoint,
threshold, overlap, stratum, matrix-key, and source-digest mutations.

R7 remains design-only. It cannot reinterpret R6 `DEFER_CONTROL_NOT_READY`,
authorize compute, or authorize promotion.

## Verification

The preregistration, R6 forensics, R6 aggregate, and Arena integrity tests
passed: 39 tests.
