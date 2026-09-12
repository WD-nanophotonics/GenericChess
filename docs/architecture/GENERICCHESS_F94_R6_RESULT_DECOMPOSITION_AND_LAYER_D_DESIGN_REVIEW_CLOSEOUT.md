# F94 R6 Result Decomposition and Layer-D Design Review

This is a pure descriptive decomposition of the completed R6 result. No
Arena, Heavy, new games, bootstrap seeds, confidence method, or classifier
rule was changed.

## Immutable source and aggregate

- Source result: `.generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json`
- Source result SHA256: `a3008d1cc0150b82bc1682e7873a9cbe6c27232f359e57479689b486c956e4fe`
- Aggregate artifact: `docs/architecture/GENERICCHESS_F94_R6_LAYER_D_AUTHORITY_REFRESH_AGGREGATE_V4.json`
- Aggregate artifact SHA256: `35a77eb779c4503e0d6bcd0d5c5b47f61276f9e3961227818ff1e7ac1118cb2b`
- Extractor: `scripts/f94_r6_result_aggregate.py`
- Progress evidence digest: `fc84255ad869240e77e4b0a38a863e86a689e48f646d0fac59300fb19b7408de`

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
It records a deterministic digest over each invocation identity, manifest hash,
and six checkpoint payload hashes, cross-checks both censoring fractions
against the frozen RESULT, and fails closed on missing, extra, malformed, or
identity-mismatched progress. These are descriptive evidence only; runtime
timing/NPS fields are not included.

## Verification

The deterministic extractor was run twice and produced identical JSON. The
focused R6, arena-integrity, and aggregate tests passed (44 tests), including
exact 108-pair retention, per-tape mean recomputation, source-SHA fail-closed
behavior, all four attribution combinations (including the actual Western
`BOTH` case), wrong-suffix and manifest-config drift checks, exact pair schema /
identity / owner / opening-integrity mutations, and progress-evidence
fail-closed checks. Runtime result/progress files remain ignored and were not
added to Git.

## R6 fallback forensics and prospective R7 review

The follow-on static audit remains zero-compute. The deterministic extractor
`scripts/f94_r6_fallback_forensics.py` produced
`docs/architecture/GENERICCHESS_F94_R6_FALLBACK_FORENSICS.json` (SHA256
`495faeb406e9d6defef84f80bd4de5817121c61286f3e6e1e1a1c848928fc3c5`). It is
bound to the same RESULT SHA and progress-evidence digest above and contains
all 29 fallback rows plus a response matrix aligned by `(tape_seed,
pair_index)` for all three matchups and both controls.

All 29 fallback rows are Standard Shogi `1024_vs_256`, parent-side at the
256-node budget, with `completed_depth=0`, `termination_reason=node_budget`,
and `decision_kind=action`: `LOW_BUDGET_PRE_ITERATION_NODE_FALLBACK`. There are
no child-side, high-budget, time/cancel, or internal-error fallback rows. The
source audit traces this to the native semantic search's legal declaration /
minimum-action fallback after no complete iterative-deepening iteration; it
keeps operational/search failures as separate categories instead of merging
them.

The design memo
`docs/architecture/GENERICCHESS_F94_R7_LAYER_D_DESIGN_REVIEW.md` compares the
strict all-pairwise gate with a prospective endpoint-primary gate and compares
any-fallback blocking with a budget/operational-stratified rule. It recommends
carrying the latter pair (endpoint `4096_vs_256` as primary; explicit strict
negative reversal and high-budget/operational fallback as blockers) only as a
pre-registered R7 hypothesis on new disjoint tapes. R6 remains frozen as
`DEFER_CONTROL_NOT_READY`; no classifier, PREP, or authority interpretation
was changed.

The new forensics, aggregate, and arena-integrity tests passed together:
`36 passed`.
