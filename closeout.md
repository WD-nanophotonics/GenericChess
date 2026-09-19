F132 closeout: Standard Shogi action-residual causal decomposition

- Work order: GENERICCHESS_F132_SHOGI_ACTION_RESIDUAL_CAUSAL_DECOMPOSITION
- Existing Courier request: GENERICCHESS-20260919-122907-2bd3ce59
- Heavy run: F132 Heavy, completed in 2718.800654888153 seconds
- Heavy envelope: f132-shogi-envelope.json
- Frozen retained roots: train 1995, dev 252, holdout 254
- Frozen F131 reproduction: pass; action top-1 0.3937007874015748; pairwise 0.6961452971418344; mean normalized teacher regret 0.14638599860007367; max-pooled T1 RMSE 2152.230646928496
- Exact oracle advantage recomposition: pass for 108502 action rows; maximum reported absolute error 0.0
- Holdout residual: RMSE 957.4164863867923; MAE 618.7399157295821; Pearson 0.8995642821035298; Spearman 0.6609335843185421
- Largest residual contribution: hand_inventory RMS 2089.5086217457747; incremental R² 0.10659274955540407; largest positive margin family on 93.5064935064935% of wrong roots
- Wrong top-1 roots: 154; mean teacher margin 1235.113753606688; capture 99, promotion 17, drop 3, quiet 46 teacher-best failures
- Local/global margin: global >=50% on 0.01948051948051948 of wrong roots; local action semantics dominate the remaining failures
- Successor-change diagnostic: absolute-residual Pearson 0.18267469554139912; residual RMSE rises from 662.067146624641 to 1308.412581371458 across standardized successor-change quartiles
- Classification: F131_LOCAL_ACTION_SEMANTICS_STILL_INSUFFICIENT
- Secondary flag: HAND_INVENTORY_RESIDUAL_DOMINANT

The frozen F131 learner and F129 oracle spectra were reused exactly. The decomposition
adds no features or learner correction and uses no self-play, search expansion, hidden
layer, optimizer comparison, or production integration. The causal audit supports a
local action-semantics insufficiency diagnosis, with hand-inventory contribution
dominant among wrong roots; no candidate or promotion was authorized. Transient result,
stage, and shard files remain under the local flow runtime and are intentionally
excluded from Git.

Validation: tests/test_f132_shogi_action_residual_causal_decomposition.py,
tests/test_f131_shogi_action_conditioned_t1_factorization.py,
tests/test_f130_shogi_rule_derived_structural_t1_augmentation.py, and
tests/test_f129_shogi_known_oracle_t1_scalar_compression.py passed.
