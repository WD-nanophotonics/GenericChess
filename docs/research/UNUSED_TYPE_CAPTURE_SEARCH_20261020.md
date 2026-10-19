# Unused duplicate declaration on captured generated 5x5 roots — 2026-10-20

## Question and controlled replay

Does an unused exact duplicate declaration change a public search decision on a
captured state from an already-frozen generated 5x5 game? The prior western
probe showed the declaration median can rescale prices but had no captured
position. This follow-up uses only the saved `candidate96` roots/rules; it adds
no game, seed, training, or source-record change.

For each of the eight generated rule seeds, choose the first family-order root
whose saved legal prefix captures material. Replay the frozen root under its
original rules and under a variant that appends `N2` as a non-promotable exact
copy of that rule's `P` movement atoms. `N2` has no promotion targets and no
starting piece; it cannot enter the captured history. The original root hash,
board, hands, side, auxiliary state, full ordered semantic action/check history,
and root legal-action set were verified. Compiler-local movement/pattern IDs
change with the rule fingerprint, so only those IDs are normalized away when
comparing the semantic history; positions and actual histories are replayed
independently under each ruleset.

The pair uses the public `AlphaBetaPlayer`, equal depth/node limits, qdepth 0,
TT/order/root-tactical off, and no time cutoff. All eight pairs completed depth
3 with the same action and PV. Several evaluator scores shifted substantially
(for example seed 522001: 3308→5079; seed 522002: 958→719), but this is score
sensitivity, not decision evidence. The added declaration changed the P price
from 0.75× to 1.54× across the tested generated rules; three profiles barely
moved it because their median was unchanged.

To test whether shallow search hid a flip, the three largest absolute P-price
multiplier departures from 1 were selected by profile alone. At the same
captured roots, a 20,000-node cap completed depth 5 and hit the cap in both
arms. All three still returned the same action/PV, while their scores differed.
The eight depth-3 and three deeper-subset summaries are in
[`data/unused_type_capture_search_20261020.json`](data/unused_type_capture_search_20261020.json).

The same preselected three roots were continued at max depth 8 with a 100,000-
node cap, still qdepth 0 with TT/order/root-tactical disabled and no time limit.
Each arm reached the cap at depth 6, 7, or 6 respectively. No first action
changed; the same states used 100,000 nodes in both arms. Caller wall times
were 17.3–19.8 seconds per arm. This extension closes the specific concern that
the earlier depth-5 result was only a 20,000-node artifact for these three
roots, but it does not broaden the fixed root sample or prove invariance.
The exact outputs are recorded as `deeper_subset_100k` in the JSON above.

## Decision

No action change appears on these frozen captured roots at the tested budgets,
even under large price-scale shifts. That closes the narrow question of whether
this saved sample provides an immediate public-search decision counterexample;
it does not prove general alias invariance, outcome utility equivalence, or a
global normalization policy. Keep the current per-declared-type normalizer and
version unchanged. Do not launch a new game panel for this question absent a
specific downstream consumer or a changed claim that would alter the decision.
Return to the current unfamiliar-rule search-gap map for the next distinct
decision-changing question.

## Post hoc outcome linkage to first candidate action

As a final read-only diagnostic, the 128 frozen `candidate96` rows were paired
by root, fixed foe and candidate owner. For the first saved query with role
`candidate`, the two arms had the same `state_before` hash in every pair where
both actions existed. Actions were canonicalized by semantic kind, actor/base
type, origin/destination and promotion target, omitting compiler-local IDs.
There were 22 same-state pairs with a different first action, 34 with the same
first action, and 8 in which neither arm had a candidate action (all terminal
outcomes). No state-hash mismatches or unpaired rows occurred.
A saved-data control audit of the 56 pairs with a candidate action confirms that
all had identical pre-move state hashes and the same recorded 8,192-node cap in
both arms. The first action changed in 22 pairs and the reported score changed
in 43; some completed depths differed even though node caps were equal. This
qualifies the result as finite equal-node decision sensitivity, not as equal-
depth comparison or causal outcome evidence.

The finite candidate-relative `static_v2 − Unit` reward contrast averaged
0.90 across the 20 complete changed-action pairs, versus 0.176 across the 34
complete same-action pairs. Two changed-action pairs contain one UNKNOWN arm;
retaining its known counterpart and bounding only the missing candidate reward
in [-1,+1] gives a conservative changed-action mean interval [0.727,0.909].
The complete-pair overall mean is 0.387; the all-pair interval is [0.344,0.406],
matching the existing fixed-foe/color aggregate after pairing. The unresolved
Unit-foe, owner-1 subcase remains [-0.0625,+0.0625].

This is post hoc association: later play contributes to reward, so it cannot
attribute the difference causally to the first action. It does show that the
saved finite utility contrast is concentrated more strongly among contexts
where the initial choices differ; it does not alter the existing scoped
`static_v2` retention decision or resolve the owner/opponent caveat. The
stratified calculations and exact UNKNOWN handling are recorded in
[`data/static_v2_first_choice_contrast_20261020.json`](data/static_v2_first_choice_contrast_20261020.json).
The derivation can be rechecked without running searches:
`.venv\Scripts\python.exe docs/research/data/static_5x5_price_20261020/candidate96/first_choice_contrast.py`.
