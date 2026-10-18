# 180-degree rotation, type relabelling and the static profile — evidence copy

Public copy of the evidence behind
`docs/research/PROFILE_TRANSFORM_INVARIANCE_20261018.md`.

Provenance: **DEEPSEEK_AUX**, branch `codex/deepseek-aux`, session
`6de032cc-45b4-4938-8700-2abdcae346aa`, 2026-10-18. Auxiliary result; no other
role has rerun it. No strength, playing-quality, utility, human-price or
game-outcome claim is made anywhere in this directory.

The study generates rules only through the existing generator
(`GeneratorConfig`, seeds 292001–292052 and 292101–292112, board sizes 6 and 8,
`classic_like`). It runs no search, no learning, no game and no fitness
evaluation. `plan.json` (SHA-256 `9892ac75…`) is the single pre-registered
design; `plan_a3.json`, `plan_evaluator_equivariance.json`,
`plan_a4.json` and `plan_a5.json` were written at the stages described in the
report, and `plan-log.json` records exactly which of them came after a run
and why, including the A5 instrument defects.

## Sanitization

The private originals under `.local_agent/profile-transform-invariance-20261018/`
contain compiler tracebacks with absolute checkout paths. This copy replaces
the checkout root with `<repo>` and any home directory with `<home>`; nothing
else is changed, and every JSON file was re-parsed after substitution so a
broken file could not be published. `make_public_evidence.py` performs that
substitution, so its own drive-letter regex is the only path-shaped token in
the published copy.

## Files

| file | bytes | SHA-256 |
|---|---:|---|
| `plan.json` | 3168 | `1aab5c000fdee89ec71e2f0a2eb4dc30bdc3cf58ebc7eff03ebf472fd6a6676e` |
| `plan_a3.json` | 4212 | `8536dbd700dd981cf0489e76e62805f98f29cd7d40cc8fef25990bdd776a24d2` |
| `plan_evaluator_equivariance.json` | 3070 | `a21d27aacb53540ee512971b4007e458e0318b17fee001dfb19307efd5c6c3fd` |
| `plan_a4.json` | 6969 | `0cb71b3ab7f625280e422c3a37208a1225cf1a4f3028f795e3bec7e9b19249d4` |
| `plan_a5.json` | 3019 | `ac50a0cc16a151168a1d7290e66d5e68709d1d459c9dc400456dd50ddebde37c` |
| `plan-log.json` | 5006 | `40fa392f640113e291a354e3f7e86c17251a396f32ee12cf8103d23a8edda1b3` |
| `results_profile_transform.json` | 290851 | `0dd0ac89beb6b195c5ace350bc33b4641f369fdbb772f2ea26baf4b78f810183` |
| `results_profile_transform_a3.json` | 128468 | `ed08a6a5ec899ff7de0ae4075c8ad75651e813530391f9824fb9a65dfa3a5582` |
| `results_a3_verification.json` | 1232 | `d685cb3248ed46718fd88c6ddb59b49b6970e1a7a1204e7035fdf422e6618c6d` |
| `results_evaluator_equivariance.json` | 68363 | `1047af3a3ae4f789bef21073086425a6d6b6081999c1b3c8dfcd9d41c45de1cc` |
| `results_promotion_zone_equivariance.json` | 345798 | `37d72d35ae96323a9857fb443c7d3371bc050cad7677c53bd1cb10d945c523bf` |
| `results_half_bonus_branch.json` | 101874 | `f5a2b860bd1c414eb8a73addd52c0a5dacdf9f659f62257818b6a50c6e4d23ff` |
| `results_zone_mechanism.json` | 154399 | `85d4429800bbfa1087c1ba09c301d35e792b51a89304397f669d5974a2c09ed3` |
| `results_zone_mechanism_heldout.json` | 27650 | `8cf8d533d45560aacbc2070189a52fc504519989419c666c31a8643382300256` |
| `results_promotion_cancellation.json` | 4608 | `dd945a96518cc2940da3194a03ed35953ca2991ffb79ba73af5ce4717609afbd` |
| `results_promotion_zone_equivariance_heldout.json` | 141565 | `b39f4ebb1baacbd83fd9931f49abc944cfab9a692094a1316859cb337ad7f7de` |
| `results_zone_effect_heldout.json` | 48962 | `3befe98f0ef1fd21b7a0ba79668ff56dcf93c06fb833827859cbb2e7839ea57b` |
| `results_zone_effect_heldout_first.json` | 67063 | `8a0dca3cc66e41e03396e5e68eef9a37e8e8337eade19969a3037a828eb8fb85` |
| `results_leaf_term_audit.json` | 218249 | `7c2673af9ba4307dbfd541514fabdca0e9cafa56019ceb1e324799f6b6720e41` |
| `scan_profile_transform.py` | 22410 | `7b5efc0c7ae45442802194f802c25e6a667bb71503ccfad819d9e382bb741101` |
| `scan_profile_transform_a3.py` | 16008 | `d988fa30e9043923450e0067f99dac39035715101fdf5ffea4f6ffda643f3ec6` |
| `verify_a3_results.py` | 4986 | `3e6b233e322e7e4d0751c6260cdfb42e948dcd4a3558784a076206bc70e77d1f` |
| `scan_evaluator_equivariance.py` | 10455 | `23080e7a681b76a52ca699a179e0af24cd1af915385e801926523a795bb214c6` |
| `scan_promotion_zone_equivariance.py` | 19635 | `6b3e36c1f3d5fc7851ee36aedc02c74ef0413d2b4af3520407d0ea620b4e11a0` |
| `scan_zone_mechanism.py` | 10825 | `89881693253fd2e7026be9fd333327ba392858d790370975178c22c6f184381c` |
| `verify_zone_mechanism_heldout.py` | 6180 | `a3e76ef48936773b555c1bf6024c8fc85dc19fabd0978db6a75a5366456ba51c` |
| `verify_half_bonus_branch.py` | 8655 | `1e441a47c9699606f4586d4a2f5b017e7d80ff644a3666ccca51057feb96051f` |
| `verify_promotion_cancellation.py` | 5409 | `7cc294025c1a6d89211ffaa5e5e6297bc76ba1ecdd1c6515da5562aeb4ca269c` |
| `verify_zone_effect_heldout.py` | 12398 | `eaddc2f61988fb3bd866988dbbedcb5a65b3558961ce76bb8e9cfb1193cb3f5f` |
| `verify_public_copy_rebuild.py` | 2030 | `a35b3c7afab8ead1492779ddb92dbcfbc6adbb15b7a0e2cb9e951cc926541e04` |
| `audit_leaf_terms.py` | 15558 | `f5a2e57da48521467aca404edf4c4b4280ced8153490d39d394bbc5646920a03` |
| `make_public_evidence.py` | 3163 | `dd71ea17e4b1caae818670682f81f2ed959ba1a261cd8bcdbb913d259047d95a` |

`manifest.json` holds the same table in machine-readable form.

## What each result file decides

| file | decision |
|---|---|
| `results_profile_transform.json` | `inconclusive` — type relabel exact (440/440), atom-only rotation refused to compile for 7 of 80 rules |
| `results_profile_transform_a3.json` | `rotation_is_a_rule_isomorphism_and_profile_invariant` — 80/80 compile, 2,327-action one-ply bijection, 440/440 exact |
| `results_evaluator_equivariance.json` | `evaluator_is_rotation_equivariant`, recorded as **uninformative**: no promotable piece is in or near its zone on those initial boards |
| `results_promotion_zone_equivariance.json` | `promotion_term_breaks_rotation_equivariance` — 24/24 in-zone cases differ, deltas {-3, +3}, promotion term only |
| `results_promotion_cancellation.json` | `whole_board_zone_makes_the_promotion_term_a_constant` — 12/12 affected rules have balanced promotable counts and a cancelling term |
| `results_zone_mechanism.json` | `zone_geometry_is_not_explained_by_atom_span` — the pre-registered predictor fails; the corrected post-hoc model matches 226/226 |
| `results_zone_mechanism_heldout.json` | `corrected_zone_model_predicts_heldout_records` — 80/80 and 80/80 on seeds 292041–292052 |
| `results_half_bonus_branch.json` | `forward_adjacency_half_bonus_branch_cannot_fire_as_coded` — `Square` vs integer-index membership |
| `results_promotion_zone_equivariance_heldout.json` | the A4 measurement repeated on 12 fresh seeds (292101–292112): 14/14 in-zone cases differ, 0/134 near/far |
| `results_zone_effect_heldout.json` | `fresh_seeds_confirms_the_zone_consequence` — predicted whole-board zone matches nonzero difference 14/14, and the difference equals the change in the summed promotion term 14/14 |
| `results_zone_effect_heldout_first.json` | the first, mis-specified formulation of that prediction (kept as an instrument-error record) |
| `results_leaf_term_audit.json` | `leaf_terms_are_type_live_except_the_half_bonus` — of the six `in`/`not in` comparisons in `evaluator.py` only the half bonus is type-impossible; the anchor-capture penalty fires and matches the expected delta in 400/400 constructed states |

## Fresh-seed consequence check (seeds 292101–292112)

The corrected zone model was fitted on seeds 292001–292040 and checked on
292041–292052. A third, independent seed set tests its *consequence* rather
than its fit: the rotated rule gets a whole-board promotion zone exactly when
the promotable base type has no atom with a negative rank direction, and a
relocated piece can only move the score when it leaves the original band zone.
All 14 usable `in_zone` cases behave as predicted, all 134 `near_zone`/`far`
cases are zero, and in all 14 nonzero cases the measured difference equals the
change in the summed promotion term (the rotated term is `+42/-42`, `+33/-33`,
`+30/-30`, `+27/-27` or `+18/-18`, i.e. a cancelling constant).

This also corrects how the value set in the report should be read. On the fit
seeds every difference was `±3` because every relevant `unit = max(1, gain //
1000)` was 1; here type `C` at seed 292108, board 8 has unit 2, so the formula
`weight * unit` gives `±6`. `±3` is therefore a property of those 40 seeds, not
of the mechanism.

Kept as executed: the first formulation of this check applied the equivalence
to all case kinds, so every near/far case with a predicted whole-board zone
counted as a mismatch (134 of them) and reported
`fresh_seeds_do_not_confirm_the_zone_consequence`. The prediction was
mis-specified, not falsified: no measured number changed, the raw first output
stays in `results_zone_effect_heldout_first.json`, and its hash is recorded in
the corrected file's `instrument_error` block.

## UNKNOWN and limits

One generator family (`classic_like`), square boards 6 and 8, 40 measurement
seeds plus two 12-seed check sets, `hand_weight = 0.9`, one relocated piece per
case. The rotated states are constructed for measurement and are not shown to
be reachable in play. The A3 legality check is one ply from the initial
position, not a game-tree isomorphism proof. Whether the half-bonus branch was
intended to fire is unknown and no repair is proposed here.

The leaf-term audit only establishes which comparisons in `evaluator.py` can be
true by type and that the anchor-capture penalty matches its own formula on
constructed states; it says nothing about how often those terms matter in
reachable play.
