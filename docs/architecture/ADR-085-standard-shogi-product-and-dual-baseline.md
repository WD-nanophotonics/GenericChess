# ADR-085: Standard Shogi product surface and dual internal baseline

Status: accepted by F25

## Decision

The certified semantic Standard Shogi definition is independently reproduced
at `generic_chess/rules/standard_shogi.py` and registered as the exact
`standard_shogi` catalog entry.  It uses the existing generic execution
dispatcher and CLI surface; no Shogi-specific branch was added to Core,
compiler semantics, transition, evaluator, search, runtime, or Native.

The production builder's gameplay fields are exactly equal to the historical
`build_semantic_shogi_ruleset()` definition.  Metadata adds the neutral,
explicit residual status `nyugyoku_supported=false`.

## Rule completeness

The current ordinary Standard Shogi product path supports movement,
capture-to-hand/demotion, drops, forced and optional promotion, nifu through a
semantic state guard, uchifuzume through the bounded semantic postcondition,
continuous-check repetition, and the existing stalemate behavior.  The
official entering-king declaration win (nyugyoku) is not represented by the
current generic terminal model and was not implemented in F25.

Therefore:

`STANDARD_SHOGI_PRODUCT_SURFACE_AVAILABLE=true`

`STANDARD_SHOGI_SEARCH_BASELINE_FROZEN=true`

`STANDARD_SHOGI_NYUGYOKU_SUPPORTED=false`

`STANDARD_SHOGI_FULL_RULE_PRODUCT_READY=false`

## Identity and evidence

Product gameplay fingerprint:

`5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345`

The ten position-only descriptors are frozen in
`tests/fixtures/f25_standard_shogi_position_descriptors.json` with SHA-256
`2429dd0ba53497b47c14fd020d2bffa1a2c89bba6fad3b91d72ff62357a0d151`.  No
AlphaSho labels, reference moves, ranks, or agreement outcomes enter search.

The full baseline is in
`tests/fixtures/f25_standard_shogi_search_baseline.json`, manifest SHA-256
`17523fba73b38640258e6aac65b92c803b8d8cf52194c5bb30e91c34dd07c121`, bound
to product/audit commit `e36816d149e67228322ce55e862dd6bcd8c973d9`.
It contains 30 fixed-node runs (128/512/2048, twice per position), 20
fixed-time runs (0.25/1.0 seconds, three repetitions per position), full
diagnostics, and per-budget medians.  All fixed-node decisions are
deterministic with zero overshoot; all fixed-time actions are legal and roots
remain unchanged.

Native was active in this environment and is recorded as
`NATIVE_PROVIDER_ACTIVE`/`NATIVE` in the fixture.  This result is descriptive,
not a strength or external-engine comparison.

## Dual-standard summary

The F24H Western authority remains manifest
`55b4e4c5253fae932bf201675b93636c80b68b7335a581711d2d475d4c4aa55b`.
F25 stores Western and Shogi metrics separately; no cross-game move, score,
accuracy, or strength comparison is made.  F25's dual summary is limited to
position count, provider mode, fixed-node completed-depth medians, and the
fixed-time throughput/timing medians recorded in the baseline fixture.

`DUAL_STANDARD_INTERNAL_BASELINE=true`

## Result

F25 is a valid product-surface and descriptive-baseline pass, not a claim of
full tournament-rule completeness.  The next boundary is
`F26_SHOGI_DECLARATION_WIN_SEMANTIC_FOUNDATION`.

