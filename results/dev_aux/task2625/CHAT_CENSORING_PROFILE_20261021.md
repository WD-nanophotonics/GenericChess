# Task2625 H=128 UNKNOWN censoring profile

## Question and method

This is a zero-search description of the frozen task2625 evaluation, following
Chat's optional suggestion. The script reads only the `HORIZON_UNKNOWN` ending,
registered rule/seed/root-family/color/endpoint slot, logged ply/query metadata,
and exact replay positions. It does not inspect `reward`, `actual_outcome`,
search values or model weights, and it launches no game or search. Frozen
training/evaluation records and caps are unchanged.

## Censoring distribution

The independently audited panel has 44 UNKNOWN endpoints: rule271001 has5,
rule271003 has39, and rules271002/271004 have none. All44 are H=128 horizon
censoring; none hit a per-slot node cap. For rule271003, unknown counts by seed
are 1977:11, 8173:11, 27182:8, 31415:9; by learner color they are 0:20 and
1:19; by endpoint they are initial:12 and TDLeaf:27. These occupy13 of16 root
families (maximum5 censored slots in one family); censoring is spread across
the fixed pool rather than limited to one start. Rule271001's five are across
three roots, seeds1977/8173/31415, four color-0 and one color-1 slot, all at
the initial endpoint.

For rule271003, 35/128 paired strata contain at least one UNKNOWN and four
strata have both endpoints censored. The other31 affected pairs have one
censored endpoint. The existing frozen finite-panel bound remains
`[-44,34]` in reward-difference sum, or `[-0.34375,0.265625]` in the mean.
Its width `0.609375 = 78/128` is exactly the worst-case uncertainty from 39
UNKNOWN endpoints, each independently ranging over `[-1,+1]`; known endpoints
are not reweighted or imputed. Existing audited aggregate terminal rewards for
rule271003 are83 losses,2 draws and132 wins across the other217 endpoints.
This descriptive census does not resolve the sign of the paired contrast.

Every censored final record has136 actions: the root contributes8 prior actions
and the registered H=128 evaluation contributes128 more. Its last logged ply
is127. Exact ruleset-aware position identities repeat in27/39 rule271003
censored histories (32/44 across both affected rules), with a maximum of three
visits to any one position; none reaches the fourfold repetition limit. Only
one of the39 rule271003 histories has unchanged global material channels for
all of its final16 transitions. These are structural descriptions, not evidence
that repetition or quiet play caused censoring; the broad material-static check
does not measure positional progress.

## Decision

Adopt the useful part of Chat's suggestion: preserve the UNKNOWN strata and
use horizon-censor rate as a predeclared design/stop criterion for any future
independent panel. The current logs do not identify an optimal horizon, and
task2629's H=256 result uses a different root pool, so it cannot estimate a
causal H effect. Do not extend or relabel task2625 and do not pool the two
panels. A later horizon choice needs a fresh outcome-blind root pool, frozen
resource caps, and a stopping rule defined before outcomes are observed.

## Reproduction

`profile_unknown_censoring.py` checks the frozen evaluation-games SHA,
reconstructs only censored histories, and emits
`run/unknown-censoring-profile.json`. Its source hashes and per-slot
structural summaries are recorded there. The pre-existing
`run/unknown-diagnostic.json`, `run/stratified-bounds.json`, and independent
evaluation audit retain authority for outcomes, terminal classification, node
caps and original paired bounds.
