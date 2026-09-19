F133 closeout: Standard Shogi resource-transition action semantics

- Work order: GENERICCHESS_F133_SHOGI_RESOURCE_TRANSITION_ACTION_SEMANTICS
- Existing Courier request: GENERICCHESS-20260919-151341-0bdf130d
- Baseline SHA: a561777bb9d1b2b4a071a8449e1928fbe9f24cb5
- Heavy run: F133 Heavy, completed in 2671.86808300018 seconds
- Frozen retained roots: train 1995, dev 252, holdout 254
- F131 frozen reproduction: pass; top-1 0.3937007874015748; pairwise 0.6961452971418344; normalized regret 0.14638599860007367; max-pooled T1 RMSE 2152.230646928496
- F132 exact decomposition: pass for 108502 actions; maximum absolute recomposition error 5.8264504332328215e-12
- Resource classes: 7 Standard Shogi structural classes; opaque type renaming preserved the signature sequence; Western Chess width was zero; mixed capture/drop/promotion controls passed
- Resource identification control: holdout RMSE 0.000278652224088315; nRMSE 1.0209750162672752e-06; R² 0.9999999999989576; Pearson 1.0000000000000002; Spearman 1.0; numerical gate pass
- HAND_EXACT_CONTROL: top-1 0.39763779527559057; pairwise 0.6960334069523595; normalized regret 0.13581891875438187; max-pooled T1 RMSE 2113.9505735718635
- F133_RESOURCE_ACTION_V1: width 49; top-1 0.37401574803149606; pairwise 0.6988214277024736; normalized regret 0.14203441825577004; max-pooled T1 RMSE 1686.2676669812988; usefulness gate pass; primary action gate fail
- Post-fit hand dominance: hand_inventory largest-positive fraction 0.9559748427672956 across 159 wrong roots
- Classification: RESOURCE_TRANSITION_SEMANTICS_DO_NOT_EXPLAIN_F131_FAILURE

The exact compiled-rule transition vector is authoritative and generic: capture-to-
hand and drop-from-hand deltas passed the mixed-mechanics controls, including promoted
captures mapping to the base resource. The resource vector identifies the exact
authoritative hand component, but adding it to F131 improves scalar T1 calibration
without materially repairing action ranking; no production integration, self-play,
search expansion, hidden layer, Adam, Arena, or promotion was authorized. Transient
result, stage, and shard files remain under the local flow runtime and are intentionally
excluded from Git.

Validation: tests/test_f133_shogi_resource_transition_action_semantics.py,
tests/test_f132_shogi_action_residual_causal_decomposition.py,
tests/test_f131_shogi_action_conditioned_t1_factorization.py,
tests/test_f130_shogi_rule_derived_structural_t1_augmentation.py, and
tests/test_f129_shogi_known_oracle_t1_scalar_compression.py passed.
