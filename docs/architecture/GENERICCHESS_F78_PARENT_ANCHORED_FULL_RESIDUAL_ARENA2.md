# GenericChess F78 Parent-Anchored Full Residual Arena2

## Decision

F78 produced a deterministic parent-anchored compact-residual candidate and
completed the authorized two-pair Arena2 stage. It is classified
`PARENT_ANCHORED_FULL_RESIDUAL_ARENA2_SURVIVES`: pair scores were `[0.5, 1.0]`,
mean pair score `0.75`, and the game record was `3W/0D/1L` for the child.

This only authorizes a later order to consider the same frozen corpus’s first
four pairs. It does not itself authorize Arena4, promotion, or any additional
training.

## Provenance and candidate

- Work order: `GENERICCHESS-F78-PARENT-ANCHORED-FULL-RESIDUAL-PAIRWISE-ARENA2`
- Baseline: `f4424c7cb31f4487c8342dad6530fa72cd7ab769`
- Parent checkpoint: `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`
- Child checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- Candidate artifact: `artifacts/f78_parent_anchored_full_residual/candidate.json`
- Candidate model SHA: `b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`
- Canonical training hash: `2c4c1c6b79a2c6b7522a23c3e69d4d29e9f90985d760fad9f0b58e99da562503`

The candidate was warm-started exactly from Gen1. Input normalization,
target scale, output bias, width, hand binding, perspective, ruleset/Native
scale, and all board/hand/dynamic/spatial/control weights stayed frozen.
Only hidden weights, hidden bias, and output weights were permitted to move.

## Trusted fit and optimizer

The F62 fit split was re-filtered with the original predicate, yielding 34
trusted roots and 246 retained action rows. Each root had equal total weight;
the pairwise target was the stable q20k/deep-consensus action versus its
retained alternatives.

The fixed optimizer was full-batch Adam for exactly 100 steps, learning rate
`0.001`, with proximal coefficient `0.001` on the three allowed parameter
blocks. There was no random initialization, minibatch, seed sweep, or
hyperparameter tuning.

| Measure | Result |
| --- | ---: |
| Trusted roots / action rows | `34 / 246` |
| Parent pairwise objective | `96.8409927822939` |
| Raw fitted pairwise objective | `2.98893935711818e-46` |
| Raw proximal term | `0.00190623825447711` |
| Raw total objective | `0.0019062382544771108` |
| Hidden-weight delta L2 | `1.3761338951198` |
| Hidden-bias delta L2 | `0.0778500202079426` |
| Output-weight delta L2 | `0.0802068047808528` |
| Chosen backtracking alpha | `1.0` |

All eight registered backtracking values from `1` through `1/128` satisfied
the safety predicates; the first value, `1.0`, was selected. Across all 48
fit roots, parent maximum absolute residual was `19,256.2350808158`, candidate
maximum was `20,128.095853123`, and the allowed cap was `38,512.4701616316`.
All 12 upper-quartile static-margin roots retained the Gen1 top action, the
candidate residuals were finite, and the trusted pairwise objective improved.
Eight Native/Python successor-state fixed-point delta checks were exact.

## Frozen Arena corpus

The evaluator-neutral Standard-Shogi corpus is
`artifacts/f78_parent_anchored_full_residual/openings.json`, with seed `780501`
and eight openings of two to six plies. Its corpus ID is
`2923f457e56454520f89c682614b3b10d07da974f03040bfc6c3a831ab41da48`.
All eight final position identities are unique, and overlap is zero with the
96 F62 roots, the F75 corpus, and the F77 corpus. F78 Arena2 used only the
first two openings.

## Arena2 result

The stage used exactly two swapped-owner pairs (four games), 512 nodes per
move for both parent and child, maximum depth 12, 8 MiB TT, one worker, fresh
engines per game, product root pruning enabled, and captured search metrics.
Caps were 256 plies, 131,072 nodes per game, four stage games, four maximum
concurrent games, and 3,600 seconds for each game and the stage.

| Measure | Result |
| --- | ---: |
| Completed games / pairs | `4 / 2` |
| Pair scores | `[0.5, 1.0]` |
| Mean pair score | `0.75` |
| Better / tied / worse pairs | `1 / 1 / 0` |
| Child game wins / draws / losses | `3 / 0 / 1` |
| Bootstrap interval | `[0.5, 1.0]` |
| Total searches | `745` |
| Parent search nodes | `190,348` |
| Child search nodes | `190,891` |
| Root-pruning telemetry | true on all rows; 0 missing |

Parent completed depths were `247 @ depth 1` and `125 @ depth 2`; child
completed depths were `235 @ depth 1` and `138 @ depth 2`. The stage had no
execution-cap reason. A second call to the same resumable entrypoint matched
status, game/pair counts, pair scores, game W/D/L, and the complete summary;
no contract failures were recorded.

The raw result remains ignored under
`.generic_chess_flow/f78-parent-anchored-full-residual-arena2/f78_results.json`.
