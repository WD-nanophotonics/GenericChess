F131 closeout: Standard Shogi action-conditioned T1 factorization

- Work order: GENERICCHESS_F131_SHOGI_ACTION_CONDITIONED_T1_FACTORIZATION
- Existing Courier request: GENERICCHESS-20260919-110400-6484a2cc
- Heavy run: F131 Heavy, completed in 1311.5639152526855 seconds
- Heavy envelope: f131-shogi-action-conditioned-t1-v1
- Frozen retained roots: train 1995, dev 252, holdout 254
- F129 reproduction: pass; base RMSE difference 1.8189894035458565e-12; static RMSE difference 2.7284841053187847e-12
- Action dataset: 87107 train, 10412 dev, 10983 holdout rows; exact feature width 42
- Weighted solver: numerical gate pass; weighted PCG/matched-ridge holdout prediction difference 1.4491650070056522e-12 normalized
- Holdout action top-1: 0.3937007874015748
- Holdout action pairwise agreement: 0.6961452971418344
- Holdout mean normalized teacher regret: 0.14638599860007367
- Max-pooled T1 holdout RMSE: 2152.230646928496
- Max-pooled T1 holdout nRMSE/R²/Pearson: 0.42072119264828567 / 0.8229936780566042 / 0.9126896963966606
- Rank diagnostic: raw width 42, active width 42, numerical rank 36, nullity 7, condition number 28.003432202818093
- Classification: ACTION_CONDITIONED_LOCAL_REPRESENTATION_INSUFFICIENT

The genericity microtests passed for Shogi-like and Western-Chess-like compiled
rulesets. The exact F129 action spectra and target definition were reused, with root-
equal action weighting and no self-play, search expansion, hidden layer, Adam, or
production integration. Max-pooling gives a much better scalar T1 RMSE than F129, but
the primary action-policy gate fails on top-1, pairwise ordering, and normalized regret;
no candidate or promotion was authorized. Transient result, stage, and shard files
remain under the local flow runtime and are intentionally excluded from Git.

Validation: tests/test_f130_shogi_rule_derived_structural_t1_augmentation.py,
tests/test_f131_shogi_action_conditioned_t1_factorization.py, and
tests/test_f129_shogi_known_oracle_t1_scalar_compression.py passed.
