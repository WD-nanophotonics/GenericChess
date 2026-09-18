# F110 Policy-v0 Failure Decomposition

Work order: `GENERICCHESS_F110_POLICY_V0_FAILURE_DECOMPOSITION`  
Baseline: `839f99f99668b6a7ef7f221f98f8f2d8ccb02947`

This is a zero-search diagnosis of the frozen F109 artifacts. It performed no
self-play, teacher query, child search, Arena run, alternate-seed fit, or new
policy training variant. Full machine-readable evidence is retained in the
ignored `.generic_chess_flow/f110-diagnosis.json`.

## Evidence integrity

| Ruleset | Frozen evaluator | Policy SHA | Roots train/dev/holdout | Complete rows | Reconstructed action features | 400-step replay |
| --- | --- | --- | --- | --- | --- | --- |
| Western Chess | `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e` | `f1e516f1d8278a3048f121df7df3191572c7073d42bb6ee31eefb78423ccdc06` | 28/4/11 | yes | exact | exact |
| Standard Shogi | `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4` | `6a4c47e7d45c5363b908f909640bdd31e4d41d700cd6cb6d1e4c8598fbefa8d8` | 30/6/11 | yes | exact | exact |

## Train-fit and oracle decomposition

Policy-v0 train top-1 agreement is only 0.4286 for Chess and 0.1333 for
Shogi. The independent per-root 24-dimensional linear action oracle reaches
only 0.5357/0.1333 top-1 and 0.6986/0.7247 pairwise accuracy on the same
train roots. Thus the low train fit is not an ordinary generalization gap;
the state-to-policy fit is being asked to express targets that the current
linear action representation cannot reliably rank.

The target-scale audit found one Chess root with `IQR=0`, but the specified
`max(IQR,1.0)` and the published `max(IQR,1e-9)` targets are identical there
(zero KL, zero entropy difference, and no teacher-top change). No Shogi root
has `IQR<1`; the target-scale contract mismatch is therefore non-material for
F109.

Exact feature collision groups with unequal q1k values were not observed in
either corpus. Hidden saturation (`abs(h)>0.95`) was observed at 0.1221 for
Chess and 0.1941 for Shogi, and is recorded as a supported secondary flag.

## Final evidence flags

| Flag | Result |
| --- | --- |
| `TARGET_SCALE_CONTRACT_MISMATCH_MATERIAL` | false |
| `TRAIN_SET_UNDERFIT` | true |
| `GENERALIZATION_GAP_SUPPORTED` | false |
| `ACTION_FEATURE_COLLISION_LIMIT_SUPPORTED` | false |
| `LINEAR_ACTION_HEAD_LIMIT_SUPPORTED` | true |
| `STATE_TO_POLICY_MAPPING_LIMIT_SUPPORTED` | false |
| `HIDDEN_SATURATION_SUPPORTED` | true |
| `TYPE_INDEX_ENCODING_LIMIT_SUPPORTED` | false |
| `NATIVE_POLICY_DUPLICATE_TRANSITION_COST` | true (separate efficiency issue) |

## Selected next correction

`ACTION_ENCODER_V1_CATEGORICAL_TYPE_EMBEDDINGS_AND_MINIMAL_CROSS_FEATURES`

This is a diagnosis only. F110 does not implement or train Policy-v1. Native
duplicate successor construction is a separate runtime optimization and is
not the explanation for offline train-set failure.
