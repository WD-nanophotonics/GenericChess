# Semantic profile ID-rename equivariance — 2026-10-20

## Question

Does the static profile preserve type values when a semantic RuleSet is
bijection-renamed through the production execution compiler?

## Method and result

tests/product/test_ai_evaluation.py::test_semantic_profile_equivariant_under_bijective_type_id_rename
uses the canonical Western RuleSet with20 semantic actions. It maps all six
piece IDs to opaque names and consistently transforms piece declarations,
initial-position base/current IDs, promotion targets and masks, drop-mask
keys, and nested typed references/selectors in the semantic definitions.
Both inputs pass through compile_ruleset_for_execution and the default
static-profile builder.

After inverse ID mapping, the median and every PieceValueProfile field match
exactly, including movement signature/raw capability, board/hand values,
promotion gains and drop fields. The canonical P remains board/hand361/325
with promotion gain2078. The profile product module passes23 tests.

## Interpretation and limits

This closes identifier equivariance for one production semantic-compiled
RuleSet path and its current profile projection. It is not a generated-rule
domain proof, semantic valuation completeness, cross-rule transfer, utility or
playing-strength result. No profile algorithm, default or price was changed;
no games or training were run.
