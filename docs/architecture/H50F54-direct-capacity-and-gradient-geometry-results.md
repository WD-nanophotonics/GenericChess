# H50 F54 direct capacity and gradient geometry diagnosis

Status: completed on 2026-09-04. Parent checkpoint: `38d91f51a2e4404825836103bac003a481ccfe00`.

## Protocol

F54 froze semantic search, TT behavior, root parallelism, fixed-point evaluation, and the existing five parameter blocks. It generated fresh evaluator-neutral semantic corpora with `GameSession`, Core legal actions, and deterministic PRNG selection only; evaluator/search was not used to select positions. Each ruleset has 64 positions, with the split frozen before fitting as positions `[0:32]` train and `[32:64]` validation.

| Ruleset | Corpus ID | Seed | 40k/80k stable | Stable train / validation | Train-key SHA | Validation-key SHA |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Western | `eacdc9f925266c02c3ea16d25f81681a352980601e2746f2dd020404e9502f6e` | 540101 | 58/64 = 0.90625 | 29 / 29 | `9770536c52141ca7ed01026291b554548b493e350a6871f6de60417137e36b75` | `2bec1397c7e717af1708d6806572c25365d140177a26efc9f6b4c0037cac98e8` |
| Shogi | `55c574b3f4226d52e252e70959fa06d3ad83fe5cd068864679da804d9c02b5a6` | 540201 | 58/64 = 0.90625 | 30 / 28 | `4c3ef61e7ad8167d9e31de854d5d5776aa7778db8a9c8f93235d756865959f32` | `af7480ef498f90aaf64797e4ab4687ed2b9ec4f6cf2049d5ad198ac36516d3e2` |

Teacher values were the current-v2 parent score converted to owner-0 value domain. Only stable positions were used for the fitting/decision gate; counts are reported above. The direct fit used ridge alpha `0.001`. All candidate decision comparisons used the stable 80k teacher and 2,000-node shallow searches. The fixed diagnostic magnitude for both TD directions was the F53 common `0.0005` full-parent-L2 scale.

## Direct linear capacity oracle

The oracle fit the deep owner-0 value residual against the existing board-material, hand-material, and three dynamic features using training positions only. The metrics below are on the untouched stable validation subset. “Applied child” is the executable Native-safe checkpoint; an unbounded oracle is shown separately where clipping occurred.

| Ruleset | Parent MSE / corr | Applied child MSE / corr | Unbounded oracle MSE / corr | Clipped params | Teacher agreement parent → child | Move flips |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Western | 1,662,712 / 0.5343 | 207,195,943 / 0.1895 | 5,397,510,663 / 0.4007 | 3 | 58.62% → 27.59% | 55.17% |
| Shogi | 962,390 / 0.4729 | 1,119,786 / 0.4862 | same as applied | 0 | 64.29% → 14.29% | 75.00% |

The Western unbounded fit is not evidence of capacity: it is not executable and is much worse than the parent on validation. After Native-safe clipping, the actual child is also much worse. Shogi's executable ridge fit slightly raises correlation but worsens MSE and decisions. No direct-fit child improved unseen teacher agreement.

## Gradient and feature geometry

The geometry probe used the same fresh corpus histories but is intentionally not the production learner: `_td_direction` reconstructs eligibility over consecutive static values along uniformly selected legal-action prefixes, with no terminal return. It is a fresh-point TD-style bootstrap for geometry, not evidence that production TDLeaf has succeeded.

| Ruleset | Prefix samples | Centered feature condition | Raw TD block energy: board / hand / dynamic | RMS-normalized TD energy: board / hand / dynamic | Raw vs RMS cosine |
| --- | ---: | ---: | ---: | ---: | ---: |
| Western | 799 | `Infinity` | 0.240% / 0% / 99.760% | 85.795% / 0% / 14.205% | 0.2152 |
| Shogi | 858 | `2.15e84` | 0.041% / 0.037% / 99.922% | 97.288% / 2.577% / 0.135% | 0.0234 |

Raw gradient energy is overwhelmingly mobility/anchor-safety dynamic energy. RMS normalization moves energy toward material coordinates, especially board features, but the resulting candidate does not improve teacher agreement: Western raw TD `58.62% → 48.28%`, RMS-normalized TD `58.62% → 55.17%`; Shogi raw TD `64.29% → 25.00%`, RMS-normalized TD remains `64.29%` with zero flips. Direction cosines against the direct ridge direction were Western `-0.0053` (raw) and `-0.0044` (RMS), and Shogi `0.0160` (raw) and `0.1681` (RMS).

Feature statistics show the same scale imbalance. Western nonzero standard deviations include board P `0.6037`, board N `0.2526`, dynamic mobility `8.2381`, and anchor safety `1.9287`; Shogi includes board P `0.3049`, hand P `0.3068`, dynamic mobility `7.4482`, promotion potential `0.9362`, and anchor safety `1.5214`. The full covariance matrices, per-feature means/std/RMS, and per-feature gradient-energy shares are retained in the transient F54 result for auditability; rank deficiency is reflected in the condition numbers above.

## Classification and boundary

Both primary rulesets independently classify as **`LOCAL_LINEAR_EVALUATOR_CAPACITY_LIMITING`** under the applied-child gate. The RMS-normalized TD direction is not a positive learned direction, and the direct ridge oracle does not improve unseen teacher policy behavior. No arena was run: the direct ridge checkpoint is an oracle-style capacity probe, not a learner-derived candidate, and neither learner-derived direction passed its policy gate.

This is a local diagnostic result, not a claim that every possible evaluator extension is impossible. It says that, under the frozen five-block generic representation and this fresh 8–40-ply corpus, the tested local linear correction cannot produce an unseen policy improvement; the next engineering boundary is richer representation or a better-posed capacity test, not another target formula. No production search/evaluator infrastructure changed.
