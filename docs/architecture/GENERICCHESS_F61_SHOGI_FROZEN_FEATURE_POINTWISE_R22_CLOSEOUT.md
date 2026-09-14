# F61 Standard-Shogi R22 frozen-feature POINTWISE_Q screen

R22 stopped at its first OOF gate. It used only the existing 24 persisted D0
roots and 157 q20/base-Q rows, with the deterministic four-fold split from
R21 (six held-out roots per fold). The width-32 hidden map was initialized
exactly from seed 59013 and frozen; only the 32 output weights and unregularized
scalar bias were solved by the fixed 1e-3 ridge objective.

No full-data candidate, external witness rerun, or Arena game was created.

## Immutable execution

- Published checkpoint: `b458397bad9d180dbbcff88a7fd4721f99b76b81`
- Parent: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Training: seed `59013`, width `32`, regularization `1e-3`, 24 roots / 157 actions
- Artifact: `.generic_chess_flow/f61-gen0-gen1-strength-triage/frozen_feature_pointwise.json`

## OOF result

| prediction | MSE | pairwise ranking accuracy | mean root top-action regret |
| --- | ---: | ---: | ---: |
| base-Q | 503,937.7261 | 0.7039 | 126.4583 |
| frozen-feature POINTWISE_Q | 973,543.6433 | 0.5364 | 350.2083 |

All three acceptance conditions fail: MSE is higher, ranking accuracy is lower,
and mean top-action teacher regret is higher than base-Q. The prescribed gate
therefore stops before creating a candidate or requesting compute approval.

## Decision

`STOP_BEFORE_FULL_CANDIDATE_OOF_GATE_FAILED`. Reducing trainable capacity in
this fixed feature map does not restore root-level generalization. No Arena or
promotion is authorized.

