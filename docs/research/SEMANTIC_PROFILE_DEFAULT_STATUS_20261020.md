# Semantic profile default status — 2026-10-20

## Question

Is the semantic movement profile merely an unselected experiment, or is it
already the product default? Can setting `evaluator_version="generic-v2"`
restore the old profile algorithm?

## Source and runtime check

`EvaluationConfig.evaluator_version` defaults to `generic-v3`; `AlphaBetaPlayer`
uses that config when the caller supplies none and builds its normal profile
through `EvaluationProfileCache`. `build_ruleset_profile` unconditionally calls
`profile_movement_atoms`; the version string is included in the profile/cache
identity but is not an algorithm selector. `Evaluator` also uses the same
projection for promotion-forward zones, with no version branch.

A cache-disabled construction on canonical Western rules returned default
version `generic-v3` and P board/hand `361/325`. Supplying only the label
`generic-v2` to the same current semantic compiled rules still rebuilt `361/325`
and labeled that profile v2. Reconstructing from the compiled legacy movement
metadata returned `1/1`. Therefore changing the version string alone does not
restore the old profile, and an extant old v2 disk cache could instead load
under the matching v2 cache identity. The verified old control is the explicit
legacy-atom reconstruction, not just a config-label change.

## Decision and limits

Adopt the first documented policy: keep v3 as the current product default
because it corrects the static input that treated a canonical executable
Western pawn as immobile and aligns promotion-forward geometry with semantic
movement. This is a semantic-correctness choice, not a demonstrated playing-
strength gain. Keep v2 legacy-atom reconstruction as a named research control;
do not imply that `evaluator_version="generic-v2"` selects it. The finite-game
evidence remains inconclusive for utility, so no universal price-quality claim
or tuning follows.

Exact read-only runtime values and source anchors are in
[`data/semantic_profile_default_status_20261020.json`](data/semantic_profile_default_status_20261020.json).
