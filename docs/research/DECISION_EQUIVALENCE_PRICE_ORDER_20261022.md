# Decision equivalence, service baselines and price ties — 2026-10-22

PRIMARY session `1f4a937c-bb7c-4ce7-bd00-598b70b34dbd`, measured backend revision
`07b4b4a24167b0643bdd892e7d2914adc3c5e120`. Raw filenames use the UTC date
2026-10-21. Science remains OPEN. No default, provider admission, learner,
AUX checkout, recurring schedule or frozen previous experiment was changed.
The only backend edit corrects an outdated kernel comment; behavior is unchanged.

The useful finding is that **completed depth, returned proof, complete optimal
sets, realized tie choice and game utility answer different questions**. Native
services improve scoped completion, but their incremental advantage over the
actual product baseline is smaller. Most finite Static/Unit differences here
are tied-set refinements; one generated state has a genuine price boundary.
Neither a price winner nor a default change is established.

## Evidence and scope

[Compact summary](data/decision_equivalence_20261022/summary.json) is the small
entry point. [Technical evidence](data/decision_equivalence_20261022/evidence.json)
is an explicit 1.31 MB projection: complete canonical inputs, all 1,452 declared
root-query outcomes, selected named diagnostics, an action/PV dictionary,
continuation records, original SHA-256 hashes and 13 own producer sources.
Constant query columns are factored, not omitted observations. Full private raw
statistics and failed preflight diagnosis remain ignored. This is not a new API,
policy framework or a claim to expose every private log.

There were 1,874 new AlphaBeta calls: 1,452 root queries plus 84 initial common-
continuation decisions and 338 new price-continuation decisions. A copied old
24-ply receipt adds no new execution. All root-query choices/PVs have independent
Core legality/full-history replay coverage, with 285 distinct choice/PV paths
and 3,247 returned PV plies across the 1,452 observations. A legal PV is not a
literal score or all-defense proof. Some winning-band scores have a legal PV
that does not end in a terminal; they are not silently converted to certificates.

The six auxiliary fixtures are exposed mechanisms, not independent rules holdout.
The nine separately declared generated rules cover boards 4/6/8, three existing
setup presets and hybrid generation enabled, with no opening-win filter or
replacement of failed seeds. All nine generated successfully; all 18 prefix0/8
roots remained ongoing. Their saved states include actual hands and a promoted
piece. This does not qualify the complete generated rule domain. Full promotion,
drop, auxiliary state and relevant history remain in execution.

## Equal clocks and the actual consumer

| Declared comparison | Slots | Core D2 completions | Service D2 completions |
|---|---:|---:|---:|
| Fresh profile/provider, whole retained-caller clock | 144, 72 pairs | 56 | 60 |
| Same setup, query-only clock | 144, 72 pairs | 58 | 64 |
| Retained evaluator/provider, per-actor warm TT | 576, 288 pairs | 221 | 240 |

The first and third frozen 20% relative D2 screens fail: +7.14% and +8.60%.
D3/D4 increases do not rescue those gates. Both fresh clock modes have 27 deeper,
45 equal and zero shallower service results. Retained objects give 115 deeper,
173 equal and zero shallower. All 90 fresh equal-depth pairs and 173 retained
pairs return identical action/score/PV. No fallback/operational error was observed.

Whole-caller time deducts measured setup before searching; query-only time does
not. Retained-object setup is reported/amortized separately, not charged to its
query deadline. All clocks are cooperative; startup, UI and network transport
are excluded. Native frontier counters are not the total number of Native check
and availability calls. Normal concurrent load remains an interpretation limit.

Crucially, constructor inspection finds the **actual public default already uses
Native legality on five of six fixtures and all nine generated rules**. The
Core-all-off arm is an authority/cost control, not that product baseline.
A new 216-slot public `choose_action` comparison therefore keeps actual default
legality and changes only the existing optional availability/check switches.
Default versus optional gives D2 48 versus50, D3 26 versus30 and only3 changed
actions in108 pairs. Both use real Native legality; optional check/availability
calls are counted separately. No default activation follows. The EP fixture's
conservative automatic admission remains unchanged despite corrected kernel
binding support; the stale comment claiming all installed kernels are broken
is corrected without changing that boundary.

## Proofs and single-decision bounds

The generated Core/service comparison has 216 slots, 8 changed selections in108
pairs and no missing/error slot. A service result can retain a completed winning
root child while its last complete uniform iteration is still D1. This actually
occurs on seed202610211649. Independent public Core observation establishes a
forcing win within **3 plies**, and an exported witness covers both opponent
replies with legal terminal winning responses. The paired Core action remains
UNKNOWN under its independent check; it is not labelled a loss. This is not a
shortest-mate or whole-game strength claim.

For a fixed common continuation value Q in[-1,1], let z include the complete Core
child state and root actor. The realized single-decision contrast is
`sum_z (countService(z)-countCore(z))*Q(z)/n`. Equal states cancel. Known terminal
or independently proved optimal-continuation values contribute constants; the
absolute unknown masses give conservative residual bounds. They are sharp for
that box relaxation, not claims that every extreme assignment is a realizable
game. No iid assumptions or future-rule confidence interval are implied.

The fresh whole-caller bound is[-1/12,1/12], retained-query bound[-7/144,7/144].
Generated-state cancellation and the independent forcing-win fact tighten its
optimal-continuation interval to[-2/27,1/9]. A separately frozen common joint
policy (existing Core D2q1/node512, TT reset each turn, both sides identical)
produces3 natural terminals and3 UNKNOWN from its6 uncancelled children; its
own conditional interval is[-1/27,2/27]. Its observed losses are not optimal-WDL
labels. Turn24 is censoring, not a new draw rule or changed max_ply.

The metalevel distinction is consistent with [Hay et al., UAI2012](https://proceedings.mlr.press/r10/hay12a.html):
computation is valued through external decisions and cost. Their sampling
bounds need assumptions that deterministic alpha-beta scores do not satisfy;
reuse and nonstationarity also matter. No Bayesian VOI scheduler, MCTS route or
new stopping policy is implemented. The successor-mass calculation above is our
finite empirical analysis, not a claimed theorem imported from that paper.

## Leaf prices and ordering prices

A frozen 144-query four-cell experiment uses all18 generated roots atD1/D2:
A=Static leaf/Static ordering, B=Unit leaf/Static ordering,
C=Static leaf/Unit ordering, D=Unit leaf/Unit ordering.
Unit assigns ordinary board CURRENT1000 and hand BASE900; anchors0. Static uses
the actual default price tables. Dynamic/escape/promotion bonuses are disabled
for this isolation; TT/root scan/q are off, ordering is on. This is not the full
product-default policy. All144 searches complete the requested depth.

Same-leaf scores agree across ordering, yet ordering changes14 D1 and11 D2 tied
selections among36 within-leaf comparisons per depth. Source diagnosis before execution confirms `score > best`: equal
scores retain traversal-first choice. These changes are allowed by contract;
no expected value or tie rule was changed to match output.

Independent complete Core trees visit12,071 entries at36 depth-roots and verify
every score and selected argmax member. D1 Static/Unit optimal sets are identical
on7 roots, with Static a subset of Unit on11. D2 has5 identical,12 subset and
1 disjoint pair. A common optimal member is not identical realized policy. A
separate uniform-over-public-optimal-actions diagnostic has D2 successor total
variation335/756 and a Q-star box bound of[-335/378,335/378]. No random tie policy
is activated, and overlapping roots are not dropped from other comparisons.

The disjoint D2 state is seed202610211648 at prefix8. Along the literal price
interpolation `(1-x)*Static+x*Unit`, the root switches at **x=85/161**. This is an
interpolation parameter, not a piece-price ratio. The extra leaf crossing927/952
does not change root optimal actions. Across the cohort308 raw point/open cells
collapse to61 consecutive constant-optimal-set runs; raw crossing count is not
policy complexity. Seventeen D2 roots admit a common optimal action throughout
this price line, a scoped finite-tree fact rather than a training gate.

Twelve public integer/rounding checks qualify the real boundary. Lifting all
coefficients by161 preserves its finite action sets without clipping (all tested
nonterminal magnitudes below1.23million versus the10million static band).
At84/161 and86/161 the nonoptimal-action margin25 safely exceeds twice the actual
maximum leaf rounding error. At85/161 component rounding shrinks a four-action
tie to one, while remaining inside the exact raw optimal set. Raw, integer-
lifted, rounded, normalized and clipped values must stay distinct; no global
precision or coefficient change is selected.

## Utility, costs and next step

For all12 A/B/C/D leaf/order/total/interaction contrasts, full-child cancellation
leaves21 outcome states rather than144 potential repeated outcome queries.
A preflight correctly finds one is the already-censored Core counterchoice;
its UNKNOWN receipt is reused verbatim. Only20 new trajectories run, making338
new decisions. There are9 natural terminal receipts and12 UNKNOWN in the21-state
union. Every interval, including C-to-D and `(D-C)-(B-A)`, remains reported.
Original144-arm incidence and exact extremal assignments independently verify
all12 box bounds. None identifies a robust price winner. The reduction is a
potential query-count saving, not a measured6.8x total speedup or free information.

The fixed continuation is the existing Static-plus-dynamic Core policy, not a
neutral oracle. These conditional trajectories neither evaluate full competing
player policies nor authorize relabelling exposure as holdout. All start/final
records strictly replay; the512 counted-node cap and full history are verified.
No old censored path is continued or refilled.

Next question is prepared, not executed: determine whether the existing dynamic
evaluator terms already alter these pure-material price regions at comparable
paid cost. All nine default price tables match this control, but the dynamic
terms were absent. On the disjoint rule X itself has promotion gain2118, while P
has0; traditional single-stage promotion assumptions would be wrong. Promotion
potential has candidate-dependent gain, integer division and base/promoted gates,
so the old affine85/161 partition cannot simply be reused. Keep all18 roots,
existing evaluator interfaces and UNKNOWN; no new learner, fit, default change,
full-WDL admission gate or AUX work is implied.
