# F61 Standard-Shogi R21 OOF shrinkage

R21 stopped at the prescribed out-of-fold gate. It used only the existing
24 persisted D0 roots and 157 q20/base-Q action rows, split deterministically
into four root-disjoint folds of six roots. No new targets, candidate
checkpoint, witness rerun, or Arena game was started.

## Immutable execution

- Published checkpoint: `7256885f53b3c8c851d564894d11742bbdf9812d`
- Parent: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Optimizer seed: `59013`
- Persisted roots/actions: `24 / 157`
- Artifact: `.generic_chess_flow/f61-gen0-gen1-strength-triage/pointwise_oof_shrinkage.json`

## OOF result

The fixed no-intercept coefficient was:

`beta = -0.04173519881909789`

Because beta is non-finite or non-positive by the acceptance rule, the run
stopped before making a scaled candidate. For reference, across 412 comparable
action pairs:

| prediction | MSE | pairwise ranking accuracy | mean root top-action regret |
| --- | ---: | ---: | ---: |
| base-Q | 503,937.7261 | 0.7039 | 126.4583 |
| base-Q + beta·OOF residual | 503,065.6020 | 0.6359 | 286.4167 |

The small MSE decrease is accompanied by a clear ranking and top-action
regression, and the beta sign itself fails the gate. Therefore scalar OOF
shrinkage does not rescue POINTWISE_Q generalization on this cached corpus.

## Decision

`STOP_BEFORE_CANDIDATE_OOF_GATE_FAILED`. No Arena was run and no promotion is
authorized. The next decision must change the learning/generalization route,
not tune beta or modify search under this work order.

