# F61 Standard-Shogi R24 linear search distillation

R24 used only the existing persisted D0 evidence: 24 roots and 157 action
rows from parent checkpoint
`2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`.
For each persisted action, the successor was reconstructed and the exact F54
board-material, hand-material, and native-dynamic vector was expressed from the
root action owner's perspective. A no-intercept ridge correction with the
frozen F54 regularization `1e-3` was fit in four deterministic 18-root/6-root
OOF folds.

## OOF gate

| Prediction | MSE | Pairwise ranking | Mean root top-action q20 regret |
| --- | ---: | ---: | ---: |
| Base Q | 503,937.7261 | 0.7038835 | 126.4583 |
| Base Q + linear delta | 1,221,340.8563 | 0.5315534 | 290.3333 |

The correction fails all three predeclared gates (MSE decrease, ranking not
lower, and regret not higher). Fold action counts were 38, 40, 38, and 41;
the exact script is `scripts/f61_linear_search_distillation.py`.

Decision: `STOP_BEFORE_FULL_CANDIDATE_OOF_GATE_FAILED`. No full-data child
checkpoint, external witness, Arena pair, or promotion claim was created.
