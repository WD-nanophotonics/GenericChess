F130 closeout: Standard Shogi rule-derived structural T1 augmentation

- Work order: GENERICCHESS_F130_SHOGI_RULE_DERIVED_STRUCTURAL_T1_AUGMENTATION
- Existing Courier request: GENERICCHESS-20260919-102320-61c52d2c
- Heavy run: F130 Heavy, completed in 1308.7573347091675 seconds
- Heavy envelope: f130-shogi-rule-derived-structural-t1-v1
- Frozen retained roots: train 1995, dev 252, holdout 254
- F129 reproduction: pass; base RMSE difference 1.8189894035458565e-12; static RMSE difference 2.7284841053187847e-12
- Structural block: RULE_DERIVED_STRUCTURAL_V1, exactly 9 scalars
- Rank diagnostic: base rank 638, augmented rank 646, increment 8; augmented active dimension 666
- Numerical gate: pass
- Representation gate: fail
- Usefulness gate: fail
- F129 base compressed holdout RMSE: 8476.168320545878
- F130 augmented holdout RMSE: 8679.479145481126
- Static direct-oracle holdout RMSE: 6088.174723192457
- Improvement vs F129: -203.31082493524627 RMSE units
- Improvement vs static baseline: -2591.3044222886656 RMSE units
- Classification: RULE_DERIVED_STRUCTURAL_AUGMENTATION_DOES_NOT_CAPTURE_T1

The genericity microtests passed for Shogi-like and Western-like compiled rulesets,
including finite outputs, exact nine-feature shape, type-name invariance, owner/board
mirror antisymmetry, and anchor-absence zero behavior. The frozen F129 shard contract
was reused and the exact T1 target was held fixed. The structural block adds independent
rank but does not capture the one-ply target on this surface; no candidate or promotion
was authorized. Transient result, stage, and shard files remain under the local flow
runtime and are intentionally excluded from Git.

Validation: tests/test_f130_shogi_rule_derived_structural_t1_augmentation.py and
tests/test_f129_shogi_known_oracle_t1_scalar_compression.py passed.
