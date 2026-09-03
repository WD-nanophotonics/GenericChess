# H50 F55 well-posed linear-capacity oracle

Date: 2026-09-04  
Work order: `GENERICCHESS-F55-WELL-POSED-LINEAR-CAPACITY-ORACLE`  
Parent checkpoint: `2aaab03485f7bbae5859c5711e310ed3a2de339d`

## Question and frozen scope

F54 established that the tested raw ridge fit did not generalize, but its
single raw-coordinate penalty was not a sufficiently well-posed capacity
oracle. F55 tests the same current-v2 five-feature evaluator representation
with a numerically competent direct fit.

Search, semantic execution, transposition tables, fixed-point evaluation, and
the five-feature representation remained frozen. No production code, feature,
or infrastructure path changed. The corpus was generated deterministically by
Core legal actions; evaluator output was not used for position selection.

The two fresh corpora each contain 96 positions, split once into 64
development/training positions and 32 untouched final-validation positions.
Teacher labels use the same 40k/80k Native searches as F54. A position is
`mate_band` when `abs(80k Native score) > 90,000,000`, the fixed static-score
band boundary. Mate-band targets are excluded from the static regression and
reported separately as a policy diagnostic.

The direct fit uses only stable, ordinary non-mate training positions. Feature
scales are training-only RMS values; zero-variance coordinates are frozen;
ridge is solved by SVD in normalized coordinates; and alpha is selected from a
fixed seven-value grid using deterministic four-fold cross-validation within
the training partition. The final validation partition selects neither alpha,
scaling, clipping, nor model form. The applied child is the executable
Native-safe checkpoint; unbounded oracle values are retained for comparison.

## Results

| RuleSet | 40k/80k stable | Stable ordinary train / validation | Active features | Condition before → after | Alpha | Clipped | Classification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Western | 83/96 (86.46%) | 54 / 28 | 7 | 98.84 → 2.65 | 1.0 | 0 | `LOCAL_LINEAR_EVALUATOR_CAPACITY_LIMITING` |
| Shogi | 87/96 (90.63%) | 60 / 27 | 13 (rank 10) | rank-deficient → rank-deficient; nonzero singular range improved | 1.0 | 0 | `LOCAL_LINEAR_EVALUATOR_CAPACITY_LIMITING` |

The F55 classification uses a 10% unseen-value MSE improvement as the
substantial-improvement threshold. Metrics below are on stable non-mate final
validation positions; values use the owner-0 convention from the learning
system.

| RuleSet | Positions | Parent MSE / MAE / corr. | Applied child MSE / MAE / corr. | MSE change | Parent policy agreement | Child policy agreement | Flip rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Western | 28 | 3,057,714 / 1,369.5 / 0.573 | 2,819,473 / 1,353.7 / 0.623 | -7.8% | 71.4% | 39.3% | 50.0% |
| Shogi | 27 | 1,378,632 / 768.0 / 0.296 | 1,390,876 / 779.2 / 0.242 | +0.9% | 59.3% | 7.4% | 74.1% |

There were no stable mate-band positions in final validation (Western had one
mate-band training position; Shogi had none). Thus no mate-band policy claim
is made. The bounded normalized-value metrics show the same direction:
Western parent/applied MSE `2.474e-5 / 2.281e-5`; Shogi
`1.115e-5 / 1.125e-5`.

## Interpretation and decision

Training-only RMS scaling materially improved Western conditioning and reduced
the coordinate-scale pathology identified in F54. Shogi remains rank
deficient even after scaling, so its SVD solution is the appropriate stable
fit for the observed design rather than a Gram-matrix inverse.

The well-posed direct fit did not produce a substantial unseen value gain in
either RuleSet under the predeclared 10% threshold, and policy agreement
decreased in both. Therefore F55 makes the local linear-capacity limitation a
credible conclusion. This is an oracle result, not evidence that online
self-learning succeeded. The next architecture stage should add a richer
generic evaluator representation; no arena was run because no learner-derived
candidate was produced.

## Provenance and verification

The raw measurement bundle is transient and remains under
`.generic_chess_flow/f55-well-posed-linear-capacity-oracle/f55_results.json`.

| RuleSet | Corpus ID | Train position-key SHA-256 | Validation position-key SHA-256 |
| --- | --- | --- | --- |
| Western | `76c2f4ab8e4b582fc649005dcfbd630fac112d24322c5f997bde5c9df6f2c076` | `a18bd35e686b8f46e0c878373b43f1104ce5c25b9e9ae8a87183941f30f1d843` | `a0eed7df6b6070cc8d14511d378d3a33ea4020c0773cb53a3bcb91aca6939081` |
| Shogi | `9c677a5395b4a557e0657bde032065ff5a0c63e4890cb653be06db559eeafada` | `99e868ae4162ee284ff67d323beb847d94ac69743af9e8eadd657b9497f7a131` | `b3de7dc29e2cc58f59851c70bda9ae68950aa0f8a7a788101a4c099927101e8a` |

Heavy diagnostic wall time was 2,590.30 seconds. The new protocol tests and
the frozen F50/F53/F54/Native/TDLeaf regression suite passed (`61 passed`).
