F134 closeout: Standard Shogi oracle-family substitution

- Work order: GENERICCHESS_F134_SHOGI_ORACLE_FAMILY_SUBSTITUTION
- Existing Courier request: GENERICCHESS-20260919-183930-c09959f1
- Baseline SHA: 8d0fcb06d0ee80476c936920f835a40943400e25
- Heavy run: F134 Heavy, completed in 2685.455500125885 seconds
- Frozen retained roots: train 1995, dev 252, holdout 254
- F131 frozen reproduction: pass; top-1 0.3937007874015748; pairwise 0.6961452971418344; normalized regret 0.14638599860007367; max-pooled T1 RMSE 2152.230646928496
- HAND_EXACT_CONTROL reproduction: pass; top-1 0.39763779527559057; pairwise 0.6960334069523595; normalized regret 0.13581891875438187; max-pooled T1 RMSE 2113.9505735718635
- Exact family decomposition: pass for 108502 actions; maximum absolute recomposition error 5.8264504332328215e-12; all split/family hashes recorded in the transient result
- Exact sanity: pass; top-1 1.0; pairwise 1.0; regret 0.0; max-pooled T1 RMSE 2.7427462696043193e-13
- Strong single-family repair: `other`; top-1 0.8740157480314961; pairwise 0.9725803605140297; normalized regret 0.004780062923998016; max-pooled T1 RMSE 232.65299629024383
- Global bundle: top-1 0.8818897637795275; pairwise 0.976315049458103; normalized regret 0.004714847174378095; max-pooled T1 RMSE 196.23495283665216
- Local bundle: top-1 0.39763779527559057; pairwise 0.6974194305361123; normalized regret 0.13544728271378478; max-pooled T1 RMSE 2080.742774390355
- Classification: SINGLE_FAMILY_CAUSAL_BOTTLENECK_SUPPORTED

The exact substitution identifies the residual `other` oracle family as the sole
strong single-family action repair under the predeclared thresholds. The global
bundle also repairs action semantics strongly, but classification precedence keeps
the single-family result because no other family is within 0.05 top-1 delta. The
hand intervention reproduces F133 exactly. No production integration, self-play,
search expansion, hidden layer, Adam, Arena, or promotion was authorized.
Transient result, stage, and shard files remain under the local flow runtime and
are intentionally excluded from Git.

Validation: tests/test_f134_shogi_oracle_family_substitution.py,
tests/test_f133_shogi_resource_transition_action_semantics.py,
tests/test_f132_shogi_action_residual_causal_decomposition.py,
tests/test_f131_shogi_action_conditioned_t1_factorization.py,
tests/test_f130_shogi_rule_derived_structural_t1_augmentation.py, and
tests/test_f129_shogi_known_oracle_t1_scalar_compression.py passed.
