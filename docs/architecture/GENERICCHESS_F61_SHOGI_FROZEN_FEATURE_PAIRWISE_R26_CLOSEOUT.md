# F61 Standard-Shogi R26 frozen-feature pairwise

R26 reused the original 24 persisted D0 roots and 157 action rows. For each
fold, the input normalization and seed-59013 width-32 hidden map were built
from the 18 training roots only. Hidden weights and bias were then frozen;
output weights started at exactly zero and were the only optimized parameters
under the existing 600-step, Adam-0.01, `PAIRWISE_RANKING` total-Q logistic
objective with regularization `1e-3`. The pre-training compact contribution
was verified to be exactly zero.

## Four-fold OOF gate

| Prediction | Pairwise ranking | Mean root top-action q20 regret | Top-1 agreement | MSE (diagnostic) |
| --- | ---: | ---: | ---: | ---: |
| Base Q | 0.7038835 | 126.4583 | 0.5833333 | 503,937.7261 |
| Frozen pairwise | 0.5703883 | 327.1667 | 0.4166667 | 2,038,450.4535 |

The ranking/regret gate fails (and both degrade), so the work stops before a
full candidate, witness searches, or Arena. Decision:
`STOP_BEFORE_FULL_CANDIDATE_OOF_GATE_FAILED`.
