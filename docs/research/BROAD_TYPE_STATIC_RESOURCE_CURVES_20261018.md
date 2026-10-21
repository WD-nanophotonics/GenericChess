# Full-type static prices, resources and geometry — 2026-10-18

Science remains OPEN. This is a scoped development comparison, not a universal
price estimate or model/default selection. PRIMARY ran it independently on
sandbox; neither auxiliary checkout, runtime nor learning/solver experiment was
modified. Complete promotion/drop/auxiliary state and relevant history remain in
the engine. A geometric coefficient is only a leaf heuristic.

## Frozen first panel and actual evidence

Eight seeds461001..8, each on6/8boards, two prefix8families and both candidate
roles give32complete roots from16generated rules. Setup and symmetry alternate
by seed; hybrids are allowed, opening-win filtering is off, generation attempts
are bounded16. All16are Native-admitted, all have promotion/drop/hybrid types;
41hybrid types and39nonunit-direction ray atoms occur. Six-board types K/P/X/A/B
and eight-board types additionally C are ALL represented in each checkpoint.
This is broader than the earlier4x4/PAX sample, not complete generated-domain
coverage. Prefix families/roles and two boards sharing a seed are linked.

Candidate Unit and existing static-v2 use Native material_scale256/T10, TT0/q0,
root_window_pruning=False, requestedD8 with8192 or32768nodes/.5s per query. The
FIXED opponent is UnitD2/32768/.5s. Horizon96afterprefix is censoring UNKNOWN,
not a draw or a changed rule max_ply512/repetition4. All256physical matches close
in559.313s, with8815queries/119617264nodes:213actual terminals,43UNKNOWN,0draws.
No learned profile was silently padded with missing B/C types: the existing
pinned learning source has a different type scope.

| Candidate/cap | W / D / L / UNKNOWN | Mean raw reward bounds | Actual nodes, both sides | Game wall seconds |
|---|---:|---:|---:|---:|
| Unit8192 |22 /0 /29 /13|[-.3125,.09375]|19356112|92.531|
| static8192 |27 /0 /26 /11|[-.15625,.1875]|18318222|91.555|
| Unit32768 |26 /0 /26 /12|[-.1875,.1875]|44279982|199.237|
| static32768 |43 /0 /14 /7|[.34375,.5625]|37662948|174.636|

Static-minus-Unit finite paired bounds are[-.25,.5] at8192 and[.15625,.75] at32768.
Posthoc descriptive linked-eight-seed envelopes are[-.625,.78125] and[-.125,1.0]:
both include0. Higher-budget6x6 finite[.5625,.6875] differs from unresolved8x8
[-.25,.8125]. Difference of budget contrasts[-.34375,1.0] does not establish an
interaction. Within-static high-minus-low[.15625,.71875] accompanies2.056times
actual nodes and1.907times game wall; the corresponding Unit interval crosses0.
These are node-cap/work curves, not pure-depth, equal-wall or population claims.
Sixteen terminal-root slots carry no queries and are retained, not filtered wins.

Independent Core reader verifies ALL256full roots/finals/history/witnesses,
8815physical commits and17025PVedges in33.343s. All8446ordinary and369terminal
PV values match their recorded integer/terminal targets; no missing PV or fallback.
This validates recorded transitions and arithmetic, not independent WDL/search
optimality or an external rules implementation.

## Opponent control interrupted; no repaired outcome fiction

A separate pre-frozen256physical-slot control changes only the fixed opponent to
staticD2, reusing the exact rules, roots and checkpoints. It does NOT rerun the
Unit-foe panel. The process disappears without its original result footer; the
journals stop advancing, the tool reports Unknown process id, and a supported
lookup restricted to the exact owned producer finds no matching process. Cause
is unconfirmed: a nearby tool/environment update is correlation, not diagnosis.
No restart, cap extension or refill occurred.

Only112closed original games exist:103terminals/9horizonUNKNOWN,3523queries and
50306726nodes. An additional12persisted queries/211769nodes belong to an unclosed
slot. All144unclosed/unstarted planned outcomes remain UNKNOWN. Including the
paid tail gives3535queries/50518495nodes; no total producer wall time is invented.
Core closed-record audit passes13.593s/7076PVedges; a separately reproducible tail
reader validates12commits/26PVedges and reconstructs an ongoing state. It does
not reconstruct an original final game/footer or count an outcome.

Planned static-minus-Unit bounds are[-1.25,1.40625] at8192 and[-.8125,1.3125] at32768.
Opponent robustness is unresolved. The explicitly labelled closed-only derived
footer serves receipt auditing, never replaces the missing original footer.
A diagnostic mask-schema counter initially failed; corrected nested-mask parsing
and its failed helper are retained. A closed-audit adapter initially omitted the
unchanged slots file; exact copying repaired only the derived arithmetic input.
Neither issue affected original matches or justifies discarding failures.

## Mechanism controls and a simpler candidate

A new finite control uses62prefix/midgame contexts (58unique full states), selected
from saved Unit8192 owner0 trajectories by a fixed ply rule, not results. On each,
Unit/static, both node caps and active-integer multipliers1/4 give496fresh queries,
9830400nodes,44.860s. All248pairs preserve action/declaration/PV/depth/node counts/
cause/fallback;240are ongoing searches and8terminal-root pairs are nonsearch
receipts. Core verifies894PVedges in6.500s. Terminal-root API score0 is a nonsearch
receipt, not a claim that Core has drawn the game. The exact integer scaling
control does not establish whole-trajectory, float-rounding, temperature/optimizer
or training invariance.

Independent direct-coordinate versus Core destination sets check boards2..24:
4899origins/29394piece-origin sets,3.790s. With K-like total4(n−1)(2n−1), ordinary
diagonal-rider total2n(n−1)(2n−1)/3 gives ratio n/6. Feys's stated half-total Bishop
convention gives n/12; these are different definitions, not evidence its whole
paper is wrong. On odd boards, half the total is not necessarily either actual
color-origin class (n3:12/8 versus half10). Overlapping compound destinations need
unions: B+K subtracts4(n−1)^2, R+K subtracts4n(n−1). Geometry excludes blockers,
royal safety and play distributions; it is not a game-value proof.

A separately frozen geo-only256physical matches compares one cheaper rule-only
candidate against BOTH fixed foes at both budgets on the SAME32roots. Coefficients
are mean unique empty-board destinations over all origins, median-nonanchor
normalization1000, existing round/clamp convention, anchor0 and hand.9; then the
standard signed checkpoint /1000 and Native256. No fitting, density sweep or
AUX hand-weight sensitivity experiment. The30min/1GiB cap is not extended.
Old interrupted144outcomes remain missing in all cross-panel bounds. A rule-only
price reader verifies16rules/88types/4512type-origins; integer tables differ from
static on all16rules, with ordering differences on only3. Ratios can differ when
rankings agree; neither difference alone establishes useful decisions.

All256new geo matches close491.781s:8097queries/102606548nodes,225terminals/31UNKNOWN.
Core verifies every fullrecord and16107PVedges in30.656s,0score differences/missing PV.

| Fixed foe / candidate cap | Geo W / L / UNKNOWN | Geo−Unit bounds | Geo−static bounds |
|---|---:|---:|---:|
| rule_static_v2__n32768 | 38 / 22 / 4 | [-0.25, 0.9375] | [-0.5, 0.6875] |
| rule_static_v2__n8192 | 20 / 36 / 8 | [-0.96875, 0.6875] | [-0.96875, 0.53125] |
| unit__n32768 | 42 / 14 / 8 | [0.125, 0.75] | [-0.25, 0.21875] |
| unit__n8192 | 27 / 26 / 11 | [-0.25, 0.5] | [-0.34375, 0.34375] |

Against Unit at32768, geo−Unit finite[.125,.75] has a descriptive seed envelope
[-.1875,1.0625], and geo−static[-.25,.21875] remains unresolved. ALL geo−static
strata and linked-seed envelopes include0. Static-foe comparisons retain the
original144missing baseline outcomes, rather than treating new geo completion
as repaired baseline evidence. No demonstrated simpler-model superiority.

The128static/geo pairs against fixedUnit have94identical COMPLETE recorded
trajectories and34first divergences, all candidate turns. Core replays3190same-
parent query pairs/3156common commits and68divergent children; all first divergences
occur with both queries reporting node_budget and equal completed depths. Seventeen
pairs have the SAME board weak-ordering including ties; their first divergence is
later than the initial root. All48available same-ordering initial query pairs
choose identically. Fourteen later same-ordering pairs reverse the two observed
ordinary-leaf preferences under BOTH exact decimal and active integer tables.
That two-leaf comparison is not a minimax or quality proof, and horizons still
censor outcomes even when the recorded paths coincide.

An optional bounded complete-CoreD2 diagnostic then tests ALL13distinct fullstate
parents underlying those17same-ordering groups. It reuses the existing complete
D2 enumeration pattern, not a new solver/API. The predeclared6min/150000total/
15000per-root-edge cap is unchanged. Twelve trees complete; one reaches its root
edge cap and stays UNKNOWN. Paid total50225edges/49614leaves includes15000edges
spent on the unknown root. Actual tree enumeration65.949s; its first input-format
attempt failed before ANY tree edge because generic record_value is not serialized
GameRecord. The adapter rebuilds each exact intended parent from saved root/commits,
checks its fullstatehash and uses canonical serialization. Original bad input/source/
receipt remains sealed; the ORIGINAL absolute deadline is retained, not restarted.
Nine completed states have disjoint static/geo optimal action sets under BOTH
exact decimal and Native256 objectives. This is concrete local evidence that
ordinal ranking does not determine these shallow preferences. It does not show
which action is stronger, explain deep selective-search utility or identify
universal piece ratios. The remaining completed intersections and capped UNKNOWN
are retained. Separate full-Core verification re-enumerates35225edges/34677leaves in35.157s,
ONLY the original completed trees; it does not finish the capped one.

An independent representation-collision diagnostic checks all16origins on4x4:
ordinary orthogonal riders and finite orthogonal leaps1..3 have identical empty
reachable sets (six targets), but11664relevant EMPTY/FRIEND/ENEMY occupancy patterns
include9728with different pseudo-mobility. At density1/4 exact mean rider567/128
versus leaper21/4; at1/2,51/16 versus9/2. All density0,1/4,1/2,3/4,1 means match
the existing analytic occupancy routine;0.268s. Off-line cells are marginalized,
not silently fixed or excluded from the full task. Empty geometry can remain a
cheap candidate but cannot be a sufficient encoding of blocking mechanisms.
This is not occupied royal-legality, a game-value proof or evidence that this
collision caused the observed game outcomes. No new representation/framework
or default follows merely from this constructed distinction.


## Primary sources and decision boundary

[Pell1994](https://cdn.aaai.org/AAAI/1994/AAAI94-212.pdf) supplies a historical
rule-derived material/mobility-adviser precedent, with a scoped game language;
it does not validate this generated domain's prices.
[Clune2007](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf) and
[Fluxplayer2007](https://cdn.aaai.org/AAAI/2007/AAAI07-189.pdf) motivate retaining
rule/goal and analysis/search-cost conditions; their evaluations are not proof
that any static geometric formula is universally sufficient.
[Stephenson et al.2021](https://arxiv.org/pdf/2105.12846), already present in the
project's route review, predicts heuristic performance from game descriptors.
Its game-held-out evaluation and heuristic-portfolio target differ from universal
piece ratios; it is not a new justification to start a duplicate AUX learner.
[Feys2026](https://arxiv.org/pdf/2605.20229), Definition2.2 and the half-Bishop/
compound discussion, is the precise convention source above. Its geometric proxy
and stated limitations motivate a cheap baseline, not human-label fitting.

Keep static/geometry/Unit and learned methods as candidates; do not deploy a
winner, add diagnostics APIs, or equate useful shallow play with identified
prices. Next choice must use the actual completed comparison and costs, preserve
all seed/role/UNKNOWN strata, and avoid repeating frozen panels merely for precision.

## Reproduction and delivery

The [sealed capsule](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/archive/broad_type_static_utility_20261018/manifest.json)
contains explicit technical originals/derived readers/failures; account and raw
Slack exports stay private. [Reproduce](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/archive/broad_type_static_utility_20261018/reproduce.py)
uses pinned parent source plus the already-published exact Core transition,
Python-S/extracted origins/no Native binary and real PRIMARY stop reads. Original
fitness/generation/training/Native queries are never rerun. Reader runtimes are
new; analyses retain original cost fields exactly. [Qualification](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/archive/broad_type_static_utility_20261018/qualification.json)
actually passes140.770s:109payloads,19derivedoutputs parked/rebuilt,16program
stages including35225Core edges from ONLY the12completedD2trees. All nonruntime
fields agree; original producer timing fields in analyses remain exact. No script
portability edit or fake stop flag; no original fitness/Native/generation/training
rerun or claim of historical timing/binary/WDL reproduction.
