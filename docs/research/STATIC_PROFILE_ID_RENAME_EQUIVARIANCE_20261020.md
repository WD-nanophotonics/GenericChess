# Static profile ID-rename equivariance — 2026-10-20

## Question

Does the rule-only legacy static profile change when piece-type IDs are
bijection-renamed while the RuleSet semantics and all ID references are mapped
consistently?

## Method and result

`tests/product/test_ai_evaluation.py::test_static_profile_equivariant_under_bijective_type_id_rename`
builds and compiles one schema-valid 6x6 legacy RuleSet with an anchor, three
ordinary movement types, a promotable source with two targets, generated drop
masks, and an initial position. The mapped RuleSet consistently renames type
declarations, initial-position base/current IDs, drop and promotion mask keys,
and every promotion target ID. Both profiles are built directly with the same
default configuration.

After inverse ID mapping, raw capability scores, movement signatures, drop
metrics, anchor/promotion flags, normalized board and hand values, promotion
option values, and the median non-anchor value are exactly equal. The entire
`PieceValueProfile` matches after replacing its renamed `type_id` with the
original ID. `tests/product/test_ai_evaluation.py` passes 22 tests, including
the new property regression.

## Interpretation and limits

This closes identifier equivariance for one legacy schema fixture and the
current static-profile builder. It adds no evidence about semantic-IR-only
rules, cross-rule transfer, cache identity, game utility, or correctness over
the complete generated rule domain. No production profile algorithm or price
default changed.
