# Numeric board ratios versus ordinal control —2026-10-18

Numeric ratio changes can create strict local shallow preferences; they have not
shown additional finite utility over a same-ordering control in this new sample.
Both candidates remain; no default, universal price or learning change follows.
This is PRIMARY's board-only comparison, not DS's hand-weight study or AUX learning.

## Changed premise and frozen design

[Broad full-type comparison](BROAD_TYPE_STATIC_RESOURCE_CURVES_20261018.md) found
nine complete D2 states with disjoint float/int optimum sets despite equal board
weakordering. Those are preference witnesses, not evidence that numeric spacing
improves play. Existing geo/static games do not implement an ordinal policy.

Before new outcomes, freeze seeds471001..8 on6x6, two prefix8families, bothroles,
two candidate models and two FIXED D2foes (Unit/static):128physical matches. Six-
board selection follows the preceding scoped positive finding; these are new
prospective seeds in an adaptively chosen regime, not an independent all-domain
holdout. Alternate classic_like/free_random and bilateral/none by seed, permit
hybrids, no opening-win filter,16generation attempts. Preserve allactualtypes,
promotion/drop/auxiliary state/repetition/history; no replacements or capped-tail
refill. This does not shrink the complete generic target to6x6.

Numeric candidate is current static-v2. Ordinal BOARD coefficients use average
ranks of its actual Native256 nonanchor board integers, median normalize1000,
round as declared, anchors0. Verify EXACT same Native weakordering including ties.
Both candidates' HAND coefficients remain exactly equal to static; no
hand-price intervention. Unit is only a fixed-foe input. The rank recipe still
requires computing static features, so this is not a cheaper rule-feature extractor.
No outcome fitting, human labels or duplicate AUX learner/solver.

Candidates request D8/32768nodes/.5s, fixedfoes D2/32768/.5s, TT0/q0 and
root_window_pruning=False. Actual depths/work remain explicit. Horizon96after
prefix leaves UNKNOWN; it is not rule max_ply or draw imputation. The20min/1GiB
cap is unchanged. Expected3–10min; actual245.782s, no extension or restart.

## Actual complete results

All128slots close:114actual terminals (including one actual draw),14UNKNOWN,
3614queries/61090023nodes. All8rules are admitted, with16complete roots/40types
across8fullprofiles. All48pairwise Native-rank checks and held-hand/profile/id
checks pass;0active board tables are identical between the candidates.

| Fixed foe | Candidate | W / D / L / UNKNOWN | Raw reward bounds | Actual nodes, both sides |
|---|---|---:|---:|---:|
| rule_static_v2 | rank_only | 18 / 0 / 12 / 2 | [0.125, 0.25] | 13109433 |
| rule_static_v2 | rule_static_v2 | 20 / 0 / 10 / 2 | [0.25, 0.375] | 12578655 |
| unit | rank_only | 20 / 1 / 7 / 4 | [0.28125, 0.53125] | 17986121 |
| unit | rule_static_v2 | 19 / 0 / 7 / 6 | [0.1875, 0.5625] | 17415814 |

Numeric-static minus ordinal is[-.34375,.28125] against Unit and[0,.25] against
static. Descriptive eight-linked-seed envelopes are[-.71875,.46875] and[-.25,.5].
Both include0;[0,.25] is not a strict positive contrast. Two families/roles/foes
sharing a seed stay linked in10000posthoc block resamples, not128independent rules
or a population-confidence guarantee. All adverse seeds and UNKNOWN remain.
No amount of changed local preferences by itself selects a utility winner.

Record costs differ from equal runtime or equal actual visited nodes. Randomized
physical execution order uses the same predeclared caps; JSON retains actual
candidate/foe counts, completed depths, causes, caller/kernel/game/producer time.
Ordinary concurrent load is an interpretation limit, not a rerun/quiet-window gate.

Core independently replays ALL128roots/finals/history/witnesses,3614commits and
8788PVedges in9.297s. All3362ordinary/252terminal PV targets agree,0fallback,
missing PV or score mismatch. This validates saved receipts, not full search
optimality, WDL/external rules authority or historical binary identity.

## Decision and reproducibility

Keep magnitude and ordinal controls separate from material-value identification.
Do not enlarge this frozen sample or refill earlier missing144staticfoe outcomes.
A further utility campaign needs a changed premise/distribution or decision, not
more repeats for narrower intervals. Existing TD/search learning remains an AUX
candidate; this result neither rejects rule-conditioned learning nor triggers a
competing learner. PRIMARY next examines a bounded complete-state/search consumer
issue with a concrete changed premise, rather than automatically launching more
price-fitness panels or interpreting these results as an Elo target.

The [17-payload capsule](../archive/ordinal_board_utility_20261018/manifest.json)
seals exact plans/inputs/physical records/costs and readers. [Reproduction](../archive/ordinal_board_utility_20261018/reproduce.py)
verifies pinned source dependencies and exact published Core transition, uses
Python-S/extracted source/no Native binary/real PRIMARY stop flags, parks four
outputs and regenerates complete receipt replay, rule-only profiles and planned
arithmetic. No original generation/Native queries/games/training are rerun.
[Qualification](../archive/ordinal_board_utility_20261018/qualification.json)
passes13.314s, allfourparkedoutputs match onnonruntimefields; original
analysiscosts remainexact. This is not historicaltiming/binary/WDL reproduction.
