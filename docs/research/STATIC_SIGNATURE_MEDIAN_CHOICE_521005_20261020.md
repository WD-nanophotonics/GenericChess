# Same-signature median choice check on saved RuleSet 521005 — 2026-10-20

## Question and frozen comparison

On the only saved 5x5 RuleSet with a repeated exact movement signature, does
counting each signature once in the profile median change fixed-budget Native
search choices? Types A and P have the same movement signature but remain
semantically distinct (including promotion metadata), so this is a sensitivity
check, not a claim that signature deduplication is the correct estimator.

The comparison reused exactly roots 521005-0 and 521005-1, with no games,
training, root replacement, product code, or profile/default change. The saved
profile SHA-256 is
4846b4c2e6d647ec4ae8c919ebaaa3132a9590f4a520c22b257311049873335c; the
roots manifest SHA-256 is
3d8f6cd488dfaba3525a91797edc8672d48c3d1a4b037f9a9d0aa05a2462da07.
Both openings replayed to their recorded state hashes before searching.

The current all-type raw median is 3.023645996; the counterfactual one-per-
exact-signature median is 2.804477276. Board values A/B/P move from
1000/855/1000 to 1078/922/1078; hand values move from 900/770/900 to
970/830/970. The source formula and caps are frozen in
data/static_5x5_price_20261020/signature_median_521005/plan.json.

## Result and limits

The first implementation attempt is invalid and is retained privately at
`.local_agent/research/521005_invalid_float_probe.json` (SHA-256
`da7cd2c759122cec5aa4e73377f4eb082237d7e197a2b83b01b1f12f1566aa3e`). It
passed normalized fractional weights to `SemanticSearchEngine`'s direct-value
adapter, which integer-converts them; that silently truncated the intended
prices. Its equal-choice observation is superseded and is not evidence. The
corrected run below uses the repository's existing
`LearnableMaterialCheckpoint` path and the same 256 fixed-point scale as the
original static-price producer.

At equal D4/4096-node, 30-second-per-query, q0, TT0 caps, both roots completed
D3 and hit the same 4096-node budget in both arms. The selected action and
three-ply PV matched on both roots. Scores were 394 versus 424 on 521005-0 and
-416 versus -448 on 521005-1 (all-type versus one-per-signature); these are
search-score differences, not outcome or utility evidence. All four PVs were
replayed through the saved GameSession and every semantic action was legal,
including the A hand drop in root 521005-0. The corrected result SHA-256 is
`79c86e08fed81629af9c42d737202f033b21e19debcd37e153e3c766fbd6207b`; root
hashes and checkpoint quantization are in result.json; independent PV replay
is in pv_replay.json.

This two-root finite comparison found no observed choice sensitivity. It does
not establish that the two normalizers are equivalent, that either is the right
reference measure, or that either is more useful: there are no outcomes for the
alternative profile. Retain the existing all-type median and close this branch.
Do not expand the price panel without a new premise that could change a model
or research choice. The next question returns to an unfamiliar-rule search
invariant, not another same-profile panel.
