# 180-degree rotation, type relabelling and the static profile — evidence copy

Public copy of the evidence behind
`docs/research/PROFILE_TRANSFORM_INVARIANCE_20261018.md`.

Provenance: **DEEPSEEK_AUX**, branch `codex/deepseek-aux`, session
`6de032cc-45b4-4938-8700-2abdcae346aa`, 2026-10-18; the zone/promotion
disjointness, source-classification, Stage 12 contact-choice, Stage 13
option-set and Stage 14 seed-closure artifacts below were added from the same
role's later session
`3d8dc073-5fcc-456e-933c-a7b6646296e5`. Auxiliary result;
no other role has rerun it. No strength, playing-quality, utility, human-price
or game-outcome claim is made anywhere in this directory.

The study generates rules only through the existing generator
(`GeneratorConfig`, seeds 292001–292052 and 292101–292112, board sizes 6 and 8,
`classic_like`). It runs no search, no learning, no game and no fitness
evaluation. `plan.json` (SHA-256 `9892ac75…`) is the single pre-registered
design; `plan_a3.json`, `plan_evaluator_equivariance.json`,
`plan_a4.json` and `plan_a5.json` were written at the stages described in the
report, and `plan-log.json` records exactly which of them came after a run
and why, including the A5 instrument defects.

Stage 7 is the one exception to that generation-only scope, and it adds no
compute: `scan_stored_games_leaf_terms.py` replays games that an earlier
session stored (board 4, seeds 59–94), with its own pre-written endpoint in
`plan_games_leaf_terms.json`. Nothing in it searches, plays or evaluates a
fitness.

## Sanitization

Stage 8 shares Stage 7's scope: `bind_reachability_to_decisions.py` replays the
same stored games and asks whether the in-zone bonus is paid to pieces that can
actually promote, with its endpoint in
`plan_bind_reachability_to_decisions.json`. It adds no search either.

`scan_zone_promotion_disjointness.py` adds no games and no search: it
regenerates the same 36 seeds and records only whether each base type's paid
zone intersects that type's compiled promotion sources, with its endpoint in
`plan_zone_promotion_disjointness.json`. Five of the 14 seeds that pay the
in-zone bonus are disjoint, so an in-zone contact ratio on those seeds is
definitional rather than measured; the artifact carries no contact count or
rate and `verify_zone_promotion_disjointness.py` rejects it if one is added.

`scan_zone_promotion_source_classification.py` shares the replay-only scope and
adds the split of the in-zone non-contact mass: is the paid square no promotion
source at all, is no allowed destination reachable, or is every target dead?
Its endpoint and its decision rule are in
`plan_zone_promotion_source_classification.json` (with one amendment written
before the run), it carries no in-zone-versus-outside rate, and
`verify_zone_promotion_source_classification.py` recomputes every bucket
independently and writes the verdict published here as
`verification_zone_promotion_source_classification.json`.

`scan_stage12_contact_choice.py` keeps that replay-only scope and asks whether
the move actually played at a contact was the promotion from the paid square,
another move from that square, or a move from elsewhere. Its endpoint, three
classes and decision rule are in `plan_stage12_contact_choice.json`, written
before the run; it carries no in-zone-versus-outside rate, and
`verify_stage12_contact_choice.py` rebuilds every position and class from the
stored move list without importing the scan. The classes are 17 promotions /
1 same-square non-promotion / 35 elsewhere / 0 absent, so the rule fires
`contact_choice_is_mixed`; a played move is not a counterfactual and no
strength, causal or utility reading is attached to it.

`scan_stage13_option_set.py` stays replay-only and asks the one follow-up that
the Stage 12 class counts cannot answer: at the 17 contacts where the promotion
from the paid square was played, was that promotion the only legal action, or
did the position offer alternatives? Its endpoint, three forcedness classes and
decision rule are in `plan_stage13_option_set.json`, written before the run. For
each rebuilt contact position it lists the legal actions, counts those that
start on the paid square, and records whether an unpromoted sibling move from
that square existed. The result is
`no_played_contact_promotion_was_forced`: 0 of 17 played promotions were forced,
all 17 had at least one unpromoted sibling, and no contact position had a single
legal action (legal-action totals run 3-22). That matters only as a
precondition - an optional promotion is at least an eligible choice under this
evaluator, whereas a forced one would have carried no preference information -
and it says nothing about whether the choice was good.
`verify_stage13_option_set.py` rebuilds the positions and the option sets from
the stored move lists without importing the scan and reproduces all 15 checks.

`analyze_stage14_seed_closures.py` adds no compute at all: it reads the stored
per-seed rows of Stages 10, 11 and 12, re-aggregates them against the published
globals, and assigns exactly one closure class to every seed with the rule fixed
in `plan_stage14_seed_closures.json` before the run. The 14 seeds that carry
in-zone observations split into 7 with contacts, 2 whose paid squares are
promotion sources but never offer a reachable allowed destination (seeds 61 and
72) and 5 whose zone is disjoint from every promotion source (seeds 63, 84, 85,
87 and 93, together the 1,312 observations already described as structural).
The decision is `every_zero_contact_seed_has_a_named_structural_closure`, with
no unexplained seed left. Its own first run is kept as a correction: it read the
observation count from the Stage 11 row, found it absent and labelled every seed
`no_in_zone_observation`; the count is read from the Stage 10 row now and the
wrong output was not carried anywhere. `verify_stage14_seed_closures.py`
re-implements the rule from the three source files and reproduces every row and
the decision (8 checks).

The private originals under `.local_agent/profile-transform-invariance-20261018/`
contain compiler tracebacks with absolute checkout paths. This copy replaces
the checkout root with `<repo>` and any home directory with `<home>`; nothing
else is changed, and every JSON file was re-parsed after substitution so a
broken file could not be published. `make_public_evidence.py` performs that
substitution, so its own drive-letter regex is the only path-shaped token in
the published copy. That script now locates the checkout root by a marker
rather than by directory depth and reads the private originals when they are
present, so running the published copy no longer writes a nested
`docs/research/docs/...` tree or fails on the Stage 7 sources.

Reproduction boundary: copying this directory somewhere else is **not** enough
to re-run the scans or verifiers. Every one of them needs the checkout root for
the `generic_chess` package and the stored game files, which live in the
git-ignored private tree, so an outside reader has the scripts, the pre-run
plans, the stored results and the verifier's own output, not a runnable
pipeline. Checked directly on 2026-10-18: `verify_zone_promotion_source_classification.py`
copied alone into a temporary directory exits 1 with
`cannot locate the worktree root above <dir>`, which is the intended failure and
not a result. Inside a checkout, `tests/specification/test_profile_transform_invariance_evidence.py`
re-checks the sizes and SHA-256 in this table and in `manifest.json` against the
stored files and rejects an artifact that was added without being listed.

## Files

| file | bytes | SHA-256 |
|---|---:|---|
| `plan.json` | 3168 | `1aab5c000fdee89ec71e2f0a2eb4dc30bdc3cf58ebc7eff03ebf472fd6a6676e` |
| `plan_a3.json` | 4212 | `8536dbd700dd981cf0489e76e62805f98f29cd7d40cc8fef25990bdd776a24d2` |
| `plan_evaluator_equivariance.json` | 3070 | `a21d27aacb53540ee512971b4007e458e0318b17fee001dfb19307efd5c6c3fd` |
| `plan_a4.json` | 6969 | `0cb71b3ab7f625280e422c3a37208a1225cf1a4f3028f795e3bec7e9b19249d4` |
| `plan_a5.json` | 3019 | `ac50a0cc16a151168a1d7290e66d5e68709d1d459c9dc400456dd50ddebde37c` |
| `plan-log.json` | 5359 | `c5a795a4cc221f7725a066e333a3c414b41130b234c3c1fc95eedb73d2273995` |
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
| `results_leaf_term_audit.json` | 290571 | `1c0486e66ad60dd80bc9a510163d449eadec40814c2eb7cc37ede41f7a40bc5f` |
| `results_stored_games_leaf_terms.json` | 38673 | `42d04b16b97db8a4eeaeb67a8dc8e87da9b3e115e38a471387d0bc5ac3a7ac1b` |
| `plan_games_leaf_terms.json` | 3384 | `d92116a58bfe17e7fc07d73023ae51c144bd9632c12462ca729a409e0070f9bb` |
| `results_static_zone_share.json` | 1020 | `a01b2e591924789591f9e229807436c3ece27838b0905405b43d47782658eeab` |
| `plan_bind_reachability_to_decisions.json` | 5055 | `dceb6678f312b96c6cdf9e9fc1fea93942ba42bbfd673bf60fa7e70133b82b02` |
| `results_bind_reachability_to_decisions.json` | 101870 | `0979ef27dda4e3e5542b6b6e3eff3340ec32502300fef66f83cb702a00b4ff80` |
| `results_contact_concentration.json` | 10154 | `2f2fe05b70ff60ae76cff8dda5a095853e2136eef45a80e0f8b177b0f0e190be` |
| `plan_zone_promotion_disjointness.json` | 2316 | `e3561e1bfcdcd76b8a5ccd7586a87876196438625694887ebbc4962b051f2ec9` |
| `results_zone_promotion_disjointness.json` | 13545 | `83b076348312882762307acafcc1c7a4c1044c1fa29678f7485d7465a7cf7507` |
| `plan_zone_promotion_source_classification.json` | 6353 | `553ad2f7f540d2743b9bf8bde3b83ada4de223675cbd328d3682c0ff338dd841` |
| `results_zone_promotion_source_classification.json` | 64409 | `317790885790abca5c3b7170b76342a6474a2381828f3988f926a8f88387b7cd` |
| `verification_zone_promotion_source_classification.json` | 3006 | `38674713b150c6a079c91c48f4b6fa7b73d20bedf5e144eedd7b61db37d05057` |
| `plan_stage12_contact_choice.json` | 3915 | `9aff2cf6b723931d5d235941d03f21c18d58a366684a0376c16d73f09f7f8c65` |
| `results_stage12_contact_choice.json` | 50205 | `dd5d347c6e885c45da8c867982abcf4a3fc7abf349d70d62a682ee9021811641` |
| `verification_stage12_contact_choice.json` | 1915 | `7240328d95c59f23570d42cbc13c8fd09e5bb14b6bbc033d0bedabef554b6ace` |
| `plan_stage13_option_set.json` | 4025 | `acc48d4f9651474f6e8e932709e5116495d355ce1f5d5f386922042cac1ecb1c` |
| `results_stage13_option_set.json` | 49664 | `b8b77064bc41958fc73a464f493a0eeddc804e9c130026b56396d782f4c9770c` |
| `verification_stage13_option_set.json` | 2417 | `07a1a1ea0f28e9916ec5d3cb4e7c9aae66fbc446639de35d0a5a5592281cd4d6` |
| `plan_stage14_seed_closures.json` | 3089 | `516900c30c7f79b66588cb7beb3da35b77ac8724f4b8e6b74298d674b339a412` |
| `results_stage14_seed_closures.json` | 10610 | `a6934149f3b6f331251fd022ded6f9d817a2d5362d446aa50b0a0ff69eb0d52e` |
| `verification_stage14_seed_closures.json` | 1837 | `85d55d08709395c0ee0910e77f1b67ad11d48a43c18eec617e9484fbc3aba66c` |
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
| `verify_public_copy_rebuild.py` | 2580 | `7c20f36da483ee8864f15b984e009a52ce7127a4c77bcf39a2dff69c26011f95` |
| `audit_leaf_terms.py` | 16581 | `f48e06fef9cf1b4ef863387f3a7908ee796e35f790a61a7465a037360fbde545` |
| `scan_stored_games_leaf_terms.py` | 11149 | `2a134c3ee8e6ff8d6635fc1e57fe9ef3276df7aaf79bd9ebd57d69f13d4b7db4` |
| `static_zone_share_boards.py` | 3066 | `fb30e7d47d639273c1da0fe9446773ec9f4ce8b88203cf783be1a879c9e2383b` |
| `bind_reachability_to_decisions.py` | 18860 | `48c5c1429f1b237dc1c4972043a4c7b6f17251173194ce48784f3e263b339bf9` |
| `verify_bind_reachability_consistency.py` | 5766 | `3e8696945ab6a84e2a327686947eebe1c39745ca26095a43b7e3454a9e484f66` |
| `analyze_contact_concentration.py` | 9537 | `3a0c74f94eb670e48742bd45af4da0b44446121a8fd07749c712e96e818609e1` |
| `scan_zone_promotion_disjointness.py` | 7131 | `03b46440c099101de44b889b589255dea8af7dec2c514607b552927217f500f5` |
| `verify_zone_promotion_disjointness.py` | 4343 | `5e3657a4ae101d9489cbd639beaf71c5ed07e227e598b3d056223cffc9b947f7` |
| `scan_zone_promotion_source_classification.py` | 23754 | `153d857499c1e6e771a0965bed4426391121f985fd3b7389001e3364dad612e0` |
| `verify_zone_promotion_source_classification.py` | 19203 | `8e088f0449829aa056fa1710e41b74bb78f4b239cda1cf413a22d77b8ce5dd5f` |
| `scan_stage12_contact_choice.py` | 13775 | `44cd708fad182add097ca558146c0f63bf060dd90182f6555d79051d46c52631` |
| `verify_stage12_contact_choice.py` | 11154 | `48dab628cb5979ac92fc95b10a882152b64e2e938aeb51f0b1f7b0de23ebaf35` |
| `scan_stage13_option_set.py` | 14710 | `0b78201952d60ea4a429288920c033fccda3c1d801bc14c2c39ae20dd6755712` |
| `verify_stage13_option_set.py` | 13890 | `70e1792eecfc4c1c991364170290b34052eb1408f0d29ec158ff4d86a25ff43a` |
| `analyze_stage14_seed_closures.py` | 10921 | `f5df1b3fb27e5800b05622e58bdf7cee5529314cb38e33834dc4038f8f56531f` |
| `verify_stage14_seed_closures.py` | 6548 | `f1fccc62ae526dd9d197c7dff061d496014274eaed4b367e8ccea16e34b4772a` |
| `make_public_evidence.py` | 6310 | `4d5dedcca8493adbdd81cb42d77fe03c777fff838bb10fee3144d747079e4760` |

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
| `results_leaf_term_audit.json` | `leaf_terms_are_type_live_except_the_half_bonus` — of the six `in`/`not in` comparisons in `evaluator.py` only the half bonus is type-impossible; the anchor-capture penalty fires and matches the expected delta in 400/400 constructed states; the audit was repeated on held-out seeds 292101–292112 with the same verdict (`verdict_heldout`) |
| `results_stored_games_leaf_terms.json` | `leaf_terms_occur_on_stored_game_paths` — replaying 182 already-stored board-4 games reproduces every stored terminal result and shows the in-zone branch on 2,489/8,083 promotable observations, the dead half-bonus condition on 3,944, and at least one anchor-attack position in every game |
| `plan_games_leaf_terms.json` | the endpoint for that replay scan, written before it ran |
| `results_static_zone_share.json` | structural check of the same definition: in-zone squares average 38.2% of the board at size 4, 21.7% at 6, 16.4% at 8, so the played 30.8% is not inflated for its board and must not be carried to other sizes |
| `plan_bind_reachability_to_decisions.json` | the endpoint for the Stage 8 replay, written before it ran, plus one amendment that adds the promotability comparison and was written before the extended run |
| `results_bind_reachability_to_decisions.json` | `in_zone_full_bonus_has_immediate_promotion_contact` with `promotability_contrast=in_zone_promotability_is_depressed_relative_to_other_promotable_pieces`: only 53 of 2,489 in-zone payments (2.13%) have a legal promotion in that position against 782 of 5,594 not-in-zone observations (13.98%), a 6.56x difference |
| `verify_bind_reachability_consistency.py` | `stored_numbers_are_self_consistent` - arithmetic and bookkeeping audit of the Stage 8 file with no replay and no search: per-game sums against the summary, the three class partitions, both rates and the ratio re-derived from the raw counts, and the four Stage 7 counts re-read from `results_stored_games_leaf_terms.json`; a deliberately perturbed copy fails it |
| `results_contact_concentration.json` | `contrast_is_seed_concentrated` - the Stage 8 file re-partitioned by seed: 7 of 36 seeds hold all 53 contacts, the top seed holds 34%, and the 5 seeds where in-zone promotability is higher supply 34/169 = 20.1% against 19/2,320 = 0.82% elsewhere |
| `analyze_contact_concentration.py` | the re-partition itself: reads the Stage 8 file, checks that nine totals re-aggregate to the published summary, and writes the per-seed table; no replay, no search, no new game |
| `plan_stage12_contact_choice.json` | the endpoint for the Stage 12 replay, its three played-move classes and its decision rule, written before the run; only the later `execution` record and `status` were added |
| `results_stage12_contact_choice.json` | `contact_choice_is_mixed` - at the 53 contacts the played move is the promotion from the paid square 17 times, another move from that square once and a move from elsewhere 35 times, with 0 contacts lacking a successor; played is not a counterfactual and no rate is carried |
| `verify_stage12_contact_choice.py` | independent replay of the same six stored files: rebuilds every position, re-derives the contact set and each played action's class without importing the scan, and reproduces all counts, per-seed rows and the decision (`all_checks_passed`) |
| `plan_stage13_option_set.json` | the endpoint for the Stage 13 replay, its forcedness classes and its decision rule, written before the run; only the later `execution` record and `status` were added |
| `results_stage13_option_set.json` | `no_played_contact_promotion_was_forced` - of the 17 contacts where the promotion from the paid square was played, 0 were forced: every one had at least one unpromoted sibling from that square, and no contact position had a single legal action (legal-action totals 3-22, actions from the paid square 2 or 3); availability only, no value reading |
| `verify_stage13_option_set.py` | independent replay of the same six stored files: rebuilds every contact position and its legal action set without importing the scan, matches every event and per-seed row, and reproduces the decision (`all_checks_passed`, 15 checks) |
| `plan_stage14_seed_closures.json` | the endpoint, the six-class closure rule and the decision rule for the Stage 14 re-read, written before the run; only the later `execution` record was added |
| `results_stage14_seed_closures.json` | `every_zero_contact_seed_has_a_named_structural_closure` - the 14 seeds with in-zone observations split 7 with contacts / 2 with a promotion source but no reachable allowed destination (seeds 61, 72) / 5 with a zone disjoint from every promotion source (seeds 63, 84, 85, 87, 93), leaving no unexplained seed; re-read only, and a closure is not a valuation |
| `verify_stage14_seed_closures.py` | re-implements the closure rule from the three stored source files instead of importing the analysis, reproduces every per-seed class and the decision, re-checks the bucket re-aggregation and rejects the withdrawn rate markers (`all_checks_passed`, 8 checks) |

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

## Does the in-zone bonus pay pieces that can promote? (Stage 8, post-hoc)

Stage 7 counted occurrences, and a share of occurrences is only meaningful if
the paid piece is in a position to promote. The zone is defined as "no empty
forward step from this square", so the opposite is plausible. Stage 8 replays
the same 182 deduplicated games (identical replay precondition, identical
2,489 / 3,944 / 1,650 occurrence counts, so the two scripts agree on the
corpus) and asks `legal_actions` for each scanned position.

Result: of the 2,489 in-zone payments, **53 (2.13%)** stand on a square with at
least one legal promotion in that same position; of the 5,594 promotable
observations that are not in the zone, **782 (13.98%)** do. The not-in-zone
rate is **6.56x** the in-zone rate, so the pre-registered contrast fires and
the full bonus is paid where immediate promotability is *lower*, not higher.
All 782 of those promotion-capable observations are in the dead-intent class -
the class whose half bonus the coded comparison never pays - and the remaining
1,650 "neither" observations have no legal promotion at all (0/1,650).

Chosen moves agree with that ordering: of 267 promotions actually played, 17
came from in-zone squares, 219 from dead-intent squares and 31 from neither.
The 21 board moves made from in-zone squares were promotions 17 times; the 307
board moves from dead-intent squares were promotions 219 times.

Reading limit that the count fixes but does not remove: 2,292 of the 2,489
in-zone observations arise during play (36 seeds) and only 197 come from the
start position (13 seeds, 63 of 182 games), so this is not a start-position
artefact; but these are depth-2 and depth-3 games from one board size, one
preset and one start position per ruleset. Zero or near-zero contact here does
not bound deeper search at boards 6 and 8, and a legal promotion being
available still does not mean search would choose it. The term is a search
preference under this evaluator, not a measure of strength.

`verify_bind_reachability_consistency.py` re-derives the reported numbers from
the stored file without a replay: per-game records against the summary, the
three class partitions, both rates and the 6.56x ratio from the raw counts, and
the four Stage 7 counts re-read from `results_stored_games_leaf_terms.json`. It
prints `stored_numbers_are_self_consistent` on the published file and fails on
a copy with one count perturbed, so "reproduces Stage 7 exactly" is checkable
offline. Agreement between two files written by the same scripts is a
bookkeeping check, not independent confirmation of the measurement.

Where the 53 contact cases can come from, read from source rather than measured
case by case: `empty_mobility` is an empty-board geometry
(`generic_chess/core/movement.py`), so "in zone" means the piece has no
advancing destination at all, while eligibility to promote is a separate
compiled frozenset of `(from, to)` pairs (`promotion_allowed` in
`generic_chess/rules/compiled.py`) that need not be a forward move. All eight
contact examples written into the results file stand on the mover's own
promotion rank; only those 8 of the 53 were inspected case by case, so this is
a checked sample and not a census. The 2.13% is therefore a measured
coincidence between an independent geometry and an independent pair set, not a
restatement of the zone definition - and it still says nothing about whether
search would ever choose such a promotion.

### The ratio is a composition average (Stage 9, post-hoc, stored numbers only)

`analyze_contact_concentration.py` reads only the Stage 8 file and
re-partitions it by seed; nine re-aggregation checks reproduce the published
summary exactly, so this is a re-weighting, not a new measurement. Of the 36
seeds, 14 contribute any in-zone observation and only 7 produce any contact;
the largest single seed supplies 18 of the 53 contacts (34%) and the top three
70%. Among the 14 seeds that have both arms, 9 have a higher not-in-zone rate
and 5 a higher in-zone rate.

That split carries the interpretation. The 5 seeds where in-zone promotability
is *higher* hold 34 of the 53 contacts from 169 in-zone observations (20.1%);
the other 31 seeds hold 19 contacts from 2,320 observations (0.82%). The pooled
2.13% against 13.98% therefore averages over two kinds of ruleset - one whose
zone acts in practice as the promotion rank and one whose zone is a pocket
unrelated to promotion. Read at seed level the defensible sentence is the weak
one, *in most of this panel the zone is not a promotion square*, not a uniform
"the bonus is paid where promotability is lowest". Thirty-six seeds support no
interval, and the contacts are repeated plies of standing pieces rather than
independent choices: 30 of the 182 games contain any contact and one game
supplies 9 of them.

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

`audit_leaf_terms.py` was run first on the 40 fit seeds and then repeated on
the held-out set 292101–292112, after that first run, through the same
`summarise()` code path and with the fit-set numbers reproduced before the
held-out block was added. The endpoint was in `plan-log.json` before either
run and did not change. Held-out counts: 53 promotable records (46 with a
positive gain), 92 zone records, 0 coded versus 2,648 index-converted target
pairs, 1,696 squares that would receive the half bonus, 1,453 constructed
states and 120 anchor-penalty triggers, all 120 matching the formula. This is a
repetition on unseen seeds, not a new prediction; it shows the source-level
statement is not specific to the fit seeds.

## Reachability on already-stored games (Stage 7, post-hoc)

The type statement above says nothing about whether those terms appear in
positions that were actually played. `scan_stored_games_leaf_terms.py` replays
the move lists of games this session had already stored (board 4,
`classic_like`, depth 2 or 3, 20,000 nodes, colour-swapped pairs) and inspects
the start position and every position after each move. All 182 distinct games
reproduce their stored terminal status, winner and ply count; 34 duplicate
move lists across stored files were dropped so nothing is counted twice.

Over 3,062 positions and 8,083 promotable-piece observations the live in-zone
branch is present 2,489 times (30.8%, in 67 of 182 games), the half-bonus
condition that the dead comparison would have paid is present 3,944 times
(48.8%, in 150 games), and 1,650 observations are neither. The anchor-attack
penalty fires in 364 owner-0 and 537 owner-1 positions and in every one of the
182 games.

Two limits. The served `zone` is the set of squares from which the base type
has no forward move at all, so "in zone" means "can no longer advance", not a
designated promotion rank; and an occurrence is not a utility, because as
coded the half bonus pays zero and this scan does not show that a repair would
change any chosen action or any result. Scope: board 4, one generator family,
one starting position per ruleset, depth 2–3 games.
