# ADR-048: Effective deep preference corpus R3

## Status

F23H accepted. V5 is the first fit-eligible deep reference artifact. It does
not fit or modify an evaluator, search, Native behavior, or any historical
fixture.

## Frozen pool and accounting

The candidate plan was fixed before split inspection: five movement-geometry
rulesets, six real A/B placements per ruleset, and a capture-mechanic branch in
two rulesets. All 30 planned candidates solved within the fixed 30,000-node /
depth-6 bounds; unresolved count is zero. No inert inventory or metadata-only
state was used.

The 30 solved representatives have 30 ruleset/fingerprint decision orbits and
no cross-split leakage. Three auxiliary-chain representatives are explicitly
marked as historical V4 duplicate orbits and excluded from fitting/validation.
The resulting effective eligible split is 20 DEVELOPMENT and 7 HOLDOUT. The
historical V1–V4 rows remain in V5 as history and are not silently reclassified.

All 20 eligible DEVELOPMENT roots are `MULTIPLY_DEPENDENT`, have non-max-ply
proofs, and have differing DRAW/LOSS root-action partitions. The five ruleset
groups contribute 3, 5, 4, 5, and 3 development orbits; the two mechanic
families are `auxiliary_reply_chain` and `capture_bad_branch`.

## Decision and next boundary

The corrected effective deep-supervision gate passes: at least 16/4 eligible
DEVELOPMENT/HOLDOUT orbits, at least four independent rulesets, no group above
35%, at least eight multiply-dependent roots, at least half with W/D/L action
diversity, at least half not max-ply-dependent, and zero leakage.

Select exactly `F23I_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R3`. F23I must consume
only the explicit V5 eligible DEVELOPMENT orbit representatives, keep the seven
HOLDOUT orbits sealed, and preserve all historical artifact hashes.
