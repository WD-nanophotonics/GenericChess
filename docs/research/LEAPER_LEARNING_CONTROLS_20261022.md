# Leaper learning controls and depth effects

DEV_AUX, sidemission. Infrastructure is the published sandbox revision
`5442b3c1d3a51398d1bfcdd403ee1a825c22c6db`; recovery fetched and checked it.
The preceding input/result revision is
`b35eeac6026886749952f775ed22023628a7571a`. Shared rules, GameSession/Core,
history/terminal and public q0 search remain unchanged. Oracle WDL is observer
data, never an experiential training input.

The main findings are that favorable parameter regions can be reached from
nonuniform starts, while individual bootstrap updates can demonstrably harm
actual-history decisions. Neither finding identifies unique material prices.
Uniform-tie controls retain a learning advantage, so the measured difference
is not entirely a favorable accident of the deployed search tie policy.

## Actual-history bootstrap regression

The two previously selected fresh Positions, indices 19468 and 20954 in the
original ABC graph, are reached legally from the real initial setup after
20 and 21 plies. Full-prefix attractors, not fresh-position labels, score
their actions. Both roots are draws. Four new public D2 queries complete with
54 nodes in .685 seconds, under the fixed 120-second whole allowance and
100,000-node/3-second query limits:

| Frozen episode-3 model | 20-ply choice | 21-ply choice |
|---|---|---|
| Before update | DRAW | DRAW |
| After update | LOSS | LOSS |

The after-choice children have actual Core all-defense winning certificates
for the opponent, with 40 and 38 nodes. Both before-choice children remain
ongoing; the preserved draw is not an immediate repetition adjudication.
The two Positions are 180-degree/color-swapped counterparts, not independent
examples; their different complete prefixes were checked separately.

Literal Core two-ply branch evaluation explains the switch. In the first
case the drawing action has heuristic score `C-B`, whereas the losing action
has score `B-1`. Their ordering flips with `2B-1-C`, from -.00146724 to
.00360962. The second case has the corresponding color-reversed features.
The entire update comes from nonterminal bootstrap terms, not a final reward
or terminal-PV target. This is an exposed counterexample to monotone policy
improvement, not an estimated population regression rate.

On the twelve unchanged episode-3 learner observations,the fixed-old-target
half-squared loss falls from .01447496 to .01444565. Revaluing both predictions
and successors on those same frozen PV features gives .01444633. Meanwhile,
the complete27-vector order moves from sector8 to9,and ideal D2uniform-tie
expected errors increase exactly2 over the33,859fresh-root distribution.
This is a concrete proxy-loss/policy-quality disagreement. These losses use
frozen old PVs,not newly selected search paths,and TD(lambda) need not minimize
either diagnostic monotonically. No oracle signal is used for the update.

## Uniform ties and a perturbation control

For each exact root, select the material-minimax action set and average its
error indicator uniformly. This replaces the searcher's particular tie choice
only in an explicitly hypothetical observer policy. A forced error means all
selected actions are suboptimal; an unsafe tie contains both optimal and
suboptimal actions. Fractional totals are exact expectations, not game counts.

| ABC model, D2; 33,859 fresh Positions | Forced errors | Unsafe ties | Expected errors | Actual public errors |
|---|---:|---:|---:|---:|
| Uniform | 497 | 2,304 | 1,638.5 | 1,799 |
| Oracle-supervised B fit | 761 | 1,803 | 1,649.9167 | 1,754 |
| Closed TD / sector 9 | 552 | 1,497 | 1,288.5333 | 1,326 |
| Adjacent sector 8 | 550 | 1,497 | 1,286.5333 | 1,324 |

Thus removing deployed tie preferences retains about 349.97 expected-error
improvement over uniform. Forced errors nevertheless increase by 55: the gain
is a change in the whole set/risk structure, not elimination of every kind of
mistake. Oracle regression fit does not necessarily optimize decision quality.
The ABA D2 expected totals are 2032.4 uniform, 1747.3 supervised, 1809.3 TD.

All twelve previously fixed near-uniform ABC chambers were scored, without
new public queries. Their D2 expected errors range from 1286.5333 to 2025.4;
the equal-chamber mean is 1659.4111. For an isotropically random small direction
around uniform, the angularly weighted mean is 1660.5882. The measure of
directions at least as good as the learned chamber is 1/8, whereas uniformly
sampling chamber IDs gives 1/6. These are two declared descriptive priors,
not learning p-values, independent trials, or a universal distribution over
prices. Twelve local chambers also do not justify describing the experiment
as necessarily one bit of information.

## Nonuniform initializations

Two algebraically opposite starts were fixed without inspecting new WDL:
`[A,B,C]=[1,1.03,1.01]` and `[1,.97,.99]`. Each receives 32 episodes with the
same eight existing legal openings, RNG-foe seeds, alternating colors, original
TDLeaf implementation and public D2. Each new run has its own declared
120-second/2,000,000-node allowance; no closed uniform-run episode was refilled.
Training takes 2.94/2.96 seconds and 3714/3702 nodes.

| Start | Final B / C | Initial → final chamber | Actual outcomes | D2 errors, initial → final |
|---|---|---|---|---|
| Plus | .9948066 / .9555079 | 0 → 9 | 31 DRAW, 1 UNKNOWN | 1883 → 1326 |
| Minus | .9476252 / .9235317 | 6 → 8 | 32 DRAW | 1522 → 1324 |

Plus episode 14 reaches its 64-ply experiment horizon. It remains UNKNOWN;
its final TD residual is withheld, while observed interior transitions remain.
Both runs make 27 weight updates, with only three/two chamber changes. All
updates reconstruct exactly from their saved literal-PV observations.

Frozen final policies complete 135,436 new public D1/D2 queries in 112.38
seconds, zero missing/UNKNOWN, within 600 seconds. Every action matches the
literal material-minimax set. Final plus/minus respectively match all actions
AND node counts of the earlier sector-9/sector-8 policies. Initial policies
are exact reuse of the existing sector-0/sector-6 runs. For plus D2, 570 errors
are fixed and 13 introduced; for minus, the net error reduction is 198.
These are finite observer distributions, not terminal-game strength.

Post-hoc actual-history evaluation also replays every saved game. Uniform,
plus and minus learners make 18/20/18 regrets among 324/319/309 actions, with
33/32/34 genuine opportunities. These counts are not a causal comparison:
different policies induce different histories despite shared openings/RNG
seeds. Their distinct-history counts are 557/550/526. The full trajectories
and decomposition stay local; compact evidence publishes the aggregates and
selected complete certificates, not a remote archive of every trajectory.

## Rotating C without filling a failed label stage

Only C changes from horizontal to vertical, retaining the original eight
actors and initial layout. Shared Core completes 46,446 vertices / 123,618
edges in 47.66 seconds. The subsequent exact action-label stage expires at
its original 120-second cap: 41,205 of 43,552 ongoing Positions are labelled,
2,347 remain unlabelled. The planned public-search stage is not launched.
There is no deadline extension, missing-slot refill or UNKNOWN-as-draw rule.

Nevertheless, missing *contrast* uncertainty can be bounded without assigning
missing labels. At 1,651 unlabelled roots the already complete graph proves
every action optimal; 696 roots could incur error. For two uniform action-set
policies with sets S,T, their total variation is
`1-|S intersection T|/max(|S|,|T|)`. An unknown [0,1] error indicator changes
the difference in expectations by at most this quantity. Sum these bounds
over the unlabelled roots; leave all 2,347 label records missing.

At D2 the full-domain expected-error difference, TD-sector-9 minus uniform,
is bounded by **[-346.8,-251.2333]**. Sector 8 minus sector 9 is exactly
**-3**: their selected sets agree on every unlabelled root that could err.
Thus these particular ideal-policy comparisons survive the geometry change.
Individual full-domain error totals remain intervals; no actual public-tie
or full-game result is inferred from the bound.

## Depth, cost and transfer limits

The fixed hash-selected resource study uses 64 fresh Positions per original
world, three frozen models, D1/2/3/4/6/8/12/16, 20,000 nodes and 1.5 seconds
per new query. D1/D2 reuse 768 completed queries. In 694.77 wall-inclusive
seconds it records 3,071 of 3,072 slots. The first ABA uniform D3 caller passed
six weights to a four-channel environment; that rejected request remains
missing, with its original cost unknown. Other requests recover with named
channel mapping and the original deadline; the failed slot is not retried.

All D6/D8 slots complete with zero errors on these 64-root samples. ABC D4
errors are 2 uniform / 2 supervised / 1 TD. At D16, ABA has 37 UNKNOWN per
model; ABC has 26/26/24. D12 has 5/5/4 UNKNOWN in ABA and 5/4/4 in ABC. These are
PV_REPLAY_TIME_CAP outputs, not draws or evidence of poor chess decisions.
Higher requested depth is not automatically a better usable decision under
a fixed full-query budget.

The full D4 census completes **258,945** slots, 384 exactly reused, zero
missing/UNKNOWN, in 1489.80 seconds under 3000 seconds. All actual chosen
actions independently match the literal cached-Core D4 minimax sets. The
complete domains retain 52,456 ABA and 33,859 ABC fresh observer Positions:

| World/model | Actual D2 errors | Actual D4 errors | Total D4 nodes |
|---|---:|---:|---:|
| ABA uniform | 2137 | 531 | 3,169,873 |
| ABA supervised | 1866 | 495 | 3,211,825 |
| ABA TD | 1930 | 499 | 3,212,423 |
| ABC uniform | 1799 | 818 | 1,788,400 |
| ABC supervised | 1754 | 853 | 1,807,173 |
| ABC TD | 1326 | 469 | 1,809,870 |

The D2 requests had larger nominal node/time ceilings, but every one completed
far below both relevant limits; the comparison measures completed depths and
their actual cost, not an equal-node match. Ordinary simultaneous local work
was present; wall times are conditional measurements, not isolated speed tests.
For ABC uniform, D4 fixes 1,024 errors while introducing 43; ABC TD fixes 920
and introduces 63. Improvement is substantial but not monotone per position.
The marginal frozen-TD advantage is473errors atD2versus349atD4 inABC,and207
versus32inABA. These within-domain contrasts show interaction between depth
and evaluation;they are not an additive law or a cross-world population effect.

One selected ABC uniform regression, index 23981, survives a separate legal
24-ply original-root history. D2 chooses DRAW with 10 nodes; D4 chooses LOSS
with 49. At the fresh root D2 scores both actions 0 (one draw, one loss),
whereas D4 scores the drawing action -1 and the losing action 0: its uniquely
preferred action is now wrong. The actual-history losing child has a rank-5,
six-node all-defense opponent win. This is a genuine horizon/representation
failure, beyond changing the deployed choice within the same tie. The two
new actual-history requests close in .89 seconds under their predeclared
120 seconds; no additional depth was appended to that closed case.

At that actual root the board,from top rank2 to rank0,is:

```
K1 A1  .
 .  . K0
 .  . C0
```

The drawing action is C0(2,0)->(1,0);the losing action is K0(2,1)->(1,0).
A separate zero-query,38-node literal Core tree fixes A=1 and varies C in
[0,8]. Its only nonterminal vectors are(-1,0,0),(-1,0,1),(0,0,1),plus actual
repetition-draw leaves. Their only positive-price order boundary is C=1.
Across both open regions and the boundary,the drawing action scores-1 and
the losing action scores C-1. Every0<C<=8 therefore prefers the loss;C=0
only creates a tie. This is an exact local positive-price obstruction atD4,
not a measurement of C's marginal contribution or proof of a universal
negative price. The initial hypothesis mistakenly clipped the second score
at zero;its assertion failure and corrected score table are retained within
the original120-second analysis deadline(40.88seconds including recovery).

An explicit fresh-start occupancy control then removes only C,retaining the
same catalog,geometry,turn and other actors. These are two new legal starts,
not transplantation of the24-ply history. Both roots are DRAW. The shared
King action(2,1)->(1,0) is LOSS with C present and DRAW without C. The present
world has1072reachablevertices/2424edges;the absent world436/952,all436fresh
vertices DRAW. Both complete in1.86seconds under one120-second whole allowance.
This isolates an action-conditional occupancy liability while leaving optimal
root WDL unchanged;it does not assign C a universal negative marginal value.

The full uniform-D6 baseline completes86,315slots in1830.10seconds under its
original2700-second allowance,128exactly reused,zero missing/UNKNOWN. Its
one-model design was estimated at about31minutes from the closed hash sample;
no old slot was retried:

| World | Uniform D6 errors / nodes | TD D4 errors / nodes | D6 versus TD-D4: fixed / new errors |
|---|---|---|---|
| ABA | 136 / 9,472,837 | 499 / 3,212,423 | 372 / 9 |
| ABC | 403 / 5,349,781 | 469 / 1,809,870 | 215 / 149 |

Depth6uniform improves aggregate quality at about2.95times the query nodes.
It does not dominate at every position;in ABC the large215/149turnover leaves
only66net fewer errors. The TD parameters were learned in ABC and frozen
before application to ABA,not trained anew in ABA. These are finite depth/
parameter resource curves,not equal-node superiority or whole-game strength.
All11,192C-absent matched controls agree on D6 action,nodes and exact WDL.
At the selected fresh index23981,D6 chooses the drawing action with218nodes;
no D6 query was appended to the separate closed24-ply actual-history control.
The completedABCportion has403errors:282WINtoDRAW and121DRAWtoLOSS. All3,641
root wins with decisive rank<=6 are found. Every missed root win has rank7..15,
and every losing action's opponent-winning child has rank7..15;there are no
violations of these sufficient mate-visibility checks. This is consistent
with unresolved longer tactics,not proof that horizon alone causes every error.

### Same full-query budget, explicit replay reserve

The auxiliary adapter now exposes an optional `pv_reserve_fraction`; its
default remains zero. The new control reserves .15seconds (10%) of the same1.5seconds for
literal replay, leaving1.35seconds for the public search. Node limits, models
and inputs are fixed. It is a new allocation arm, not a replacement for any
closed UNKNOWN result or an engine-speed claim.

All768 D12/D16 control requests finish in583.87seconds under1200seconds, with
zero missing/UNKNOWN and zero exact action errors. All768 literal PVs replay
and match their terminal outcome or actual leaf features/value. Compared with
the reused baseline,214 previously unusable inputs now have usable completed
iterations; none of the554 previously usable choices gets worse WDL or becomes
unknown. Requested-depth completions fall from554 to530: availability is gained
at the cost of some deepest iterations. The maximum observed full-query time
is1.41264seconds. Earlier baseline timing/concurrency differs; this is not an
isolated causal timing trial. Actual training/default play has not adopted the
reserve, so no training acceleration or strength improvement is claimed.

There is also a limited mathematical transfer statement. If all nonterminal
material vectors belong to the same 27-vector inventory, preserving their
complete score order, zero and the separated mate-distance ordering preserves
ideal finite-depth q0 optimal-action sets by induction through min/max. The
board need not stay 3x3. This does not identify unique prices, establish WDL,
or guarantee identical bounded-search implementation behavior.

An actual 4x4, symmetric eight-actor test uses the same A/B/C movement types,
64 legal random opening histories, three frozen models and D1/2/3/4/6. All
960 public queries complete in 57.80 seconds, zero UNKNOWN/missing. The two
same-chamber models agree on action AND nodes at all 320 paired decisions.
The adjacent-chamber model also chooses the same actions at these contexts,
but differs in nodes at nine decisions. Neither stronger play nor whole-rule
equivalence follows. This is not a rerun of the closed 5x5 MM graph timeout.

Claude's Gordon reference was checked against the
[original NIPS 2000 paper](https://proceedings.neurips.cc/paper_files/paper/2000/file/04df4d434d481c5bb723be1b6df1ee65-Paper.pdf).
Its bounded-region result assumes a linear approximator and suitable decaying
step sizes, among other conditions. Our fixed-step, tanh/search-leaf learner
does not inherit that theorem. Its bounded parameter region is also a different
object from these finite leaf-order chambers. It supplies a useful caution,
not a convergence or optimality guarantee for this experiment.

## Delivery and next decision

Reusable changes are a nonuniform-start argument in the existing runner,
uniform-tie expectation/TV analysis, and a D3/D4 cached-Core observer. The latter
is restricted to fresh non-pass Leaper histories: the earliest recurrence is
the root after four plies. It rejects D5+, which needs more history. Literal
Core transition tests cover real four-ply repetition, plus named-channel
mapping and incomplete-label bounds. No second rules or deployed search
implementation is introduced.

Generated graph/query journals stay ignored. The current compact scientific
JSON is `data/leaper_parameter_regions_20261022.json`; fixed source/parameters,
budget failures and exact local receipts are retained. Old experiment limits,
stops and ACTIVE 90-minute same-chat recurrence remain unchanged.

All155related tests pass. Three independently replayed actual-history
certificates cover every defender move and actual winning terminal. The full
D4census has258,945literal minimax matches. D6action labels and legality are
cross-checked,but its complete PV paths were not exported for a second replay;
literal-PV admission is enforced by the actual public adapter. No D5+cached
history shortcut is used. The next useful question is whether rotating C alone
removes the shared King's occupancy liability in the explicitly legal fresh
setup,followed by selected residual mechanisms rather than an automatic D8grid.
The research segment closes at a safe checkpoint with61.25confirmed effective
minutes. Administrative publication/transport time is excluded;all bounded
research producers have exited and the next question remains executable.
