# GenericChess F60: Disjoint Policy, Objective, and Distribution Validation

Status: completed offline validation; deployable-child and arena gates were not entered.

Parent checkpoint: `790695da03cd4bdcc9412f3566517063b0c674e3`

Work order: `GENERICCHESS-F60-DISJOINT-POLICY-OBJECTIVE-AND-DISTRIBUTION-VALIDATION`

## Scope and protocol

F60 used fresh Standard Shogi source pools and did not reuse F59 roots. The frozen representation/search spectrum was retained; no evaluator, search, or engine architecture change was made. The experiment trained four distributions (`D0_RANDOM_REACHABLE`, `D1_V2_SELFPLAY`, `D2_V2_PV_CORRIDOR`, and equal-fit `D12_D1_D2_MIX`) with three objectives (`POINTWISE_Q`, `PAIRWISE_RANKING`, and `SOFT_POLICY_DISTILLATION`) and three seeds (`59011`, `59012`, `59013`). Every model was evaluated on all three final holdouts: 36 final matrix cells.

The primary metric was stable, ordinary, equal-budget q20 normalized teacher regret. Root40/root80 and mate-band checks were secondary. The development selector used the equal-weight D1/D2 aggregate, then selected the median development seed. The D0 pointwise median-seed model was the development-only reference for candidate eligibility.

## Fresh-source and disjointness evidence

Source IDs recorded by the run:

| Distribution | Source ID | Pool roots | fit/dev/final roots |
|---|---|---:|---:|
| D0 random reachable | `b2c6f0a194ee781e86440c1537cc95c84a7b2982cda8c77236b5d5c91b3a0cec` | 96 | 48 / 24 / 24 |
| D1 v2 self-play | `0223dc817fe1876e714d66f91c9c6fecf444af38b215b42078049beacdae987d` | 132 | 67 / 37 / 28 |
| D2 v2 PV corridor | `c7810c8fd1fd083b90b7939d72e75224642a6d829f1795a84e7417a77d903773` | 96 | 48 / 24 / 24 |

The position-key overlap matrix was zero off-diagonal for every D0/D1/D2 pair. D2 was generated from an independent self-play/base-root pool (`d2_independent_from_d1: true`). The source-group overlap matrix was also zero off-diagonal across every distribution/split pair.

Source-group unit accounting matters here: D0 uses one opening-position group per root, so its unit counts are 48 / 24 / 24. D2 uses one independent base-root group per selected PV descendant, so its unit counts are 48 / 24 / 24. D1 used whole self-play trajectories: the recorded split diagonals show 4 / 2 / 3 independent trajectory units for fit/dev/final (9 trajectory units assigned to the requested splits; the configured pool contained 12 games). Thus D1's 67 / 37 / 28 root counts must not be interpreted as 132 independent games. The preserved result records unit counts and split root totals, but not the individual per-trajectory root-size list; that serialization gap is carried into the next-order correction rather than being fabricated after the run.

## Teacher stability and mate exclusions

No root80 or retained-q20 mate-band roots/actions were present in any distribution. Stable rates and secondary budget agreement were:

| Distribution | Stable roots | Stable rate | 10k→20k top-1 agreement | 40k↔80k agreement |
|---|---:|---:|---:|---:|
| D0 | 92 / 96 | 0.9583 | 0.9583 | 0.8854 |
| D1 | 126 / 132 | 0.9545 | 0.9545 | 0.9242 |
| D2 | 95 / 96 | 0.9896 | 0.9896 | 0.8958 |

The primary fit/dev/final metrics used ordinary usable roots after these stability filters: D0 45 / 24 / 23, D1 62 / 36 / 28, and D2 47 / 24 / 24.

## Frozen development selection

The selected development configuration was D0 training with `PAIRWISE_RANKING`, seed `59012`, selected by the median development-only seed rule. Its aggregate D1/D2 development metrics were normalized regret `0.303283`, ranking accuracy `0.627323`, and top-1 agreement `0.446759`.

The D0 pointwise seed-59012 reference had development normalized regret `0.347626`, ranking accuracy `0.529582`, and top-1 agreement `0.465278` in the recorded reference seed table. Candidate eligibility still required per-distribution material improvement, non-catastrophic behavior, action changes, policy agreement/ranking improvement, and seed robustness against that reference.

## Final matrix summary

Entries below are means over the three seeds for each train distribution/objective, evaluated on each final holdout. Lower normalized regret is better.

| Train distribution | Objective | D0 final | D1 final | D2 final |
|---|---|---:|---:|---:|
| D0 | pointwise | 0.4243 | 0.3761 | 0.4087 |
| D0 | pairwise | 0.4634 | 0.3290 | 0.4093 |
| D0 | soft policy | 0.3271 | 0.3893 | 0.4571 |
| D1 | pointwise | 0.4099 | 0.3074 | 0.5270 |
| D1 | pairwise | 0.4989 | 0.3037 | 0.4201 |
| D1 | soft policy | 0.4944 | 0.3587 | 0.4471 |
| D2 | pointwise | 0.3968 | 0.3441 | 0.3706 |
| D2 | pairwise | 0.5982 | 0.0798 | 0.3299 |
| D2 | soft policy | 0.5169 | 0.3175 | 0.4138 |
| D12 mix | pointwise | 0.3723 | 0.3011 | 0.3348 |
| D12 mix | pairwise | 0.5830 | 0.1717 | 0.3155 |
| D12 mix | soft policy | 0.4916 | 0.2588 | 0.3353 |

The full-matrix classification helpers reported `POLICY_OBJECTIVE_MISMATCH_SUPPORTED` and `STATE_DISTRIBUTION_MISMATCH_SUPPORTED` for reproducible combinations somewhere in the matrix. These labels are not permission to deploy a particular candidate.

## Candidate gate and decision

The selected D0/Pairwise/59012 candidate changed 22 root action choices (11 on D1 and 11 on D2), and the selected configuration improved at least one policy metric. However:

- aggregate selected normalized regret was `0.384165` versus the recorded reference `0.375413`, so material aggregate regret improvement was false;
- D1 passed the material-regret subcheck but not the top-1/ranking subcheck;
- D2 passed the top-1/ranking subcheck but not the material-regret subcheck;
- seed robustness count was 2/3, below the required all-seed robustness condition;
- `eligible_for_shallow_policy_gate` was `false`.

Therefore F60 stopped before the sign-reversed deployable residual, real 2k child gate, and arena. The offline teacher-regret result is not an external playing-strength claim.

## Follow-up corrections for the next order

1. Preserve the exact per-trajectory root-size list for D1 in the durable result, not just source-unit counts and root totals.
2. Reconcile the offline teacher-imitation gate with the user's priority that external engines are arena/benchmark opponents, not ground-truth move/score judges. A technically valid decision-changing candidate may need a small paired parent/champion arena triage before teacher disagreement alone vetoes it; this is a next-order policy change, not an F60 expansion.
3. Before any real iterative self-improvement loop, require a T0 terminal contract: `tdleaf_update` must reject `terminal='ongoing'` artificially truncated trajectories or use an explicit bootstrap target. F60/F59 used truncation only for state collection; this does not invalidate historical F50–F53 main-training results, which did not use this cutoff.
