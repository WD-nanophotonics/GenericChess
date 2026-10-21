# Leaper information exposure and conditional geometry — 2026-10-22

The retained ABA training scarcely distinguishes the useful B=1/2 decision
boundary, and its sole sampled action boundary does **not** distinguish WDL.
Rotating C changes exact strategic outcomes on many matched positions, but
public initial-position admission substantially narrows the counterfactual
domain. Numerical TD movement, conditional contribution and good search
parameters remain different objects. No new training, price or product default
is selected.

Compact evidence: [leaper_information_geometry_20261022.json](data/leaper_information_geometry_20261022.json).
This is a post-hoc study of exposed records and complete caches, not independent
held-out validation or a set of independent rule samples. Full raw graphs and
journals remain local; selected complete rules, records and proof paths publish
with the compact evidence. Aggregate-only entries do not claim remote access to
all raw trajectories or verification by another researcher.

## Infrastructure and preserved boundaries

Latest fetched sandbox is `559aa80dc224250dc30135b3cb4696e389f0d134`.
Its changes since `d1017250c8720113000105b7519f6beffa774d0a` are research and
operations documents; shared package code/tests are unchanged. The 238 shared
package files still match the committed mainline. The two AUX learner modules
remain the only package additions. Rules, GameSession/Core and public search
are reused; no new rule executor or product search is introduced.

The four closed ABA arms are uniform, plus, minus, and the changed 16-opening
pool. Their 128 records contain 1,333 completed learner queries. Original models,
opponent randomness, budgets, failures and the coverage arm's single
`HORIZON_UNKNOWN` are unchanged. No public query or training episode was rerun.
Slack channel coverage and all 24 tracked threads were read; no new advice was
present. The old uncertain report was not resent. Recurrence is unchanged.

## What the learner actually saw

Literal shared-Core D2 alternatives retain each query's complete actual prefix.
Every saved choice belongs to the complete minimax argmax at its actual frozen
weights. Selected PVs are independently replayed; a material-only observer is
never a replacement for actual terminal authority.

| Closed arm | Queries | Different argmax at B=1/4 versus 3/4 | Disjoint supports |
| --- | ---: | ---: | ---: |
| uniform | 335 | 2 | 2 |
| plus | 387 | 2 | 2 |
| minus | 335 | 2 | 2 |
| coverage16 | 276 | 1 | 1 |

All seven occurrences are the **same full history**, after B0 a1-b2. The two
relevant B1 moves are c1-b0 and c1-b2. Their root-player D2 scores are `-B` and
`B-1`; they tie at B=1/2. Exact full-prefix action labels, in the recorded
five-action order, are `[-1,0,0,0,-1]`: both competing moves are DRAW. The other
three action labels remain visible rather than being discarded.
Equal optimal-play WDL does not identify equal return against the random foe
or eliminate every useful signal in those experiences.

In ABA, nonterminal material is `a+bB` with integer a in [-2,2], b in [-1,1].
Two such leaves have no positive crossing strictly between 0 and 1 except 1/2;
decisive terminal scores dominate throughout this interval. Min/max selects
one of these leaves. Thus 1/4 and 3/4 represent the two open D2 action regions,
not just two arbitrary grid points. On these retained query histories their
uniform-tie WDL quality is identical across the two regions. This statement
does not include B=0,1/2,1 or the plus arm's B>1 region, actual tie-policy
equality, future training paths, or every reachable game position.

Chosen-PV B support was 36/67/36/32, much larger than 2/2/2/1 action-boundary
exposure. A nonzero feature derivative is not strategic discrimination.

The observer completes in 9.605 cumulative process seconds under 300 seconds.
Two repaired failures are retained: confusing dataclass action logs with the
public action serializer, then parsing a rational score with `float` instead
of `Fraction`. The final tree/replay counter is 8,025 visits including failed
attempts. Independent PV validation adds 2,658 edges, giving 10,683 charged
visits/edges, still below the original 50,000 allowance. No cap was reset.

## Frozen TD credit and what a win conceals

All 128 B updates are reconstructed to 1e-12 using both equivalent sums:
eligibility at each TD-error endpoint, and each gradient origin carried through
later errors. Removing one term would be a frozen algebraic attribution;
it would not predict retraining with changed future weights and actions.

| Arm | Total B change | Final-terminal-term contribution | Origins at the sampled boundary |
| --- | ---: | ---: | ---: |
| uniform | -.04804845 | -.00040187 | +.00011329 |
| plus | -.02144715 | -.00040163 | +.00009223 |
| minus | -.04752196 | -.00040211 | +.00013821 |
| coverage16 | -.03652823 | -.00040187 | -.00001724 |

Terminal terms can carry eligibility from earlier positions. They are not the
same as gradients originating at terminal PVs, which are zero. Censoring still
withholds the unknown final target.
The remaining terms include search-to-search transitions into terminal PVs;
a small final-outcome term does not mean all terminal information is small.

Full-prefix exact observation covers all 128 retained games, 1,333 queries and
930 distinct action histories, in 171.243 seconds under 900. Learner/foe WDL
gap sums are 2/12, 6/12, 2/12 and 2/14. For every trajectory,

`endpoint learner-value - initial learner-value = foe gaps - learner gaps`.

For the 127 actual terminal games the endpoint is the actual payoff. For the
censored game it is an exact observer potential, **not** a played outcome.
Coverage16 episode24 enters a draw-only region at absolute ply49 and has
theoretical endpoint DRAW, but its original rollout remains UNKNOWN; it is not
silently added to the observed draws or strength statistics.

Uniform episode22 is an explicit winning-game counterexample: K0 b0-a0 changes
WIN to DRAW; K0 b0-b1 preserves WIN. The random foe then gives the win back.
An all-defense winning strategy before the mistake is independently replayed
through actual training rules, six Core nodes. Minus contains the identical
trajectory; coverage16 episode25 is a second, distinct winning trajectory with
a learner error. Three occurrences are not three independent replications.

There are 6/6/6/3 query-root versus chosen-PV WDL disagreements. In particular,
two actual nonterminal PV leaves have the same zero material vector and opposite
one-ply wins. Their all-defense paths replay through the original training
rules. Both associated query roots are DRAW: leaf representation aliasing must
not be misreported as two wrong root decisions. One extra ply recognizes the
mate at each selected leaf; this alone proves no whole-root D3 quality gain.
The two winning leaves differ in side to move. A third full-prefix DRAW
witness matches the player0 winning leaf's side and complete inventory
(one K and one A per owner), not only its zero difference vector. Thus even
turn and total counts do not resolve this particular value alias. Position
and history both vary; their individual contributions are not isolated here.

## A region with no strategic outcome variation

Reverse reachability from every decisive terminal leaves a forward-closed set
of 8,088 of 57,437 ABA positions. No possible policy can reach mate from these
positions. In this restricted capture-removal/repeat-two world every full-prefix
continuation therefore draws. A minimax DRAW elsewhere does not have this
property: a player can still blunder to mate.

The reusable graph observer `draw_only_closure` checks graph sinks/indices and
does not generate moves. Two regressions distinguish a draw with a possible
mate from an all-draw cycle and independently check actual Core successors.
Completeness remains a premise; a resource-truncated graph is not admissible.

Closed-region learner queries are 239/335, 285/387, 239/335 and 165/276.
Their nonterminal B-gradient supports are 4/20/4/5. Gradient origins there
contribute -.00089333, -.00833606, -.00083653 and -.00078679 to B respectively.
These shared-parameter changes can affect other states; no strategic outcome
can improve *inside* this region. Endpoint attribution differs because it
includes eligibility originating earlier outside the region.

## Geometry prevalence and the initial-position correction

Existing complete AC horizontal/vertical caches share 8,554 physical positions
after fingerprint mapping. Their graph fresh-history comparison has 429 root
WDL changes and 797 shared-action WDL changes; 220 positions change a shared
action while preserving the root value. All 7,128 C-absent controls agree.
These are constructed fresh-history contexts, including side1 and checks;
they are not all permissible RuleSet initial boards.

An attempted direct witness compilation failed with `INITIAL_ANCHOR_ATTACKED`.
That failure is retained. We then tested actual public RuleSet/GameSession
initialization without bypassing validation:

| Domain | Both axes admitted | Root WDL changes | Shared-action WDL changes |
| --- | ---: | ---: | ---: |
| Actual side0 fresh starts | 2,835 | 143 | 348 |

This subset has 479 C-present and 2,356 C-absent starts. Eighty-nine positions
preserve root WDL while changing a shared action. The 1,196 rejected side0
positions and 4,523 side1 contexts are excluded from this initial-start table,
not erased from the explicitly constructed-context comparison.

Deletion controls fix all other actors/squares and remove owner1 A and/or C.
Among 760 matched graph contexts across all eight worlds, 172/188 H/V
interaction contrasts are nonzero, 284 change with axis, and three C-with-A
marginal signs strictly reverse. These last three do **not** survive admission
as actual fresh initial boards.

Of 404 side0 candidates, 238 initialize successfully in **all eight worlds**;
166 fail at least one. In this stricter domain, 49/50 H/V interactions are
nonzero, 92 change with axis, and **zero** C-with-A marginal signs strictly
reverse across axes. One admitted horizontal world retains the previously
known reversal of C's contribution when A is removed; vertical has none here.
Payoff contrasts use owner1 values {-1,0,1}; they are not intrinsic prices or
linear conservation laws. Graph-intersection selection and correlated positions
prevent population prevalence claims.

## Composition and depth change useful parameter regions

Requiring owner0 A and B still present leaves only 13 of the 238 fully admitted
starts; the other 225 are excluded explicitly. All four H/V, C-present/absent
counterfactuals are ongoing. Keep A=C=1 and compare B=0,1/2,1,3/2,2,5/2,3,4.
In this asymmetric inventory B's leaf coefficient is 0 or1, C's is0 or-1,
and A's is-1,0 or1; integer boundaries suffice for the tested [0,4] domain.
This is a common, exposed position distribution, not a new learned table.

The entries are sums of exact uniform-tie suboptimal-action probabilities over
13 roots, not win rates or numbers of independent errors:

| World | D2 B=1/2 | D2 B=1 | D2 B=3/2 | D4 B=1/2 | D4 B=1 | D4 B=3/2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| horizontal C | 0 | 13/6 | 3 | 5/3 | 5/3 | 2 |
| vertical C | 1/2 | 5/6 | 1 | 1 | 1 | 1 |
| C absent, either axis | 0 | 0 | 0 | 0 | 0 | 0 |

Without C every tested B cell is indistinguishable by this quality measure.
Adding horizontal C makes the (0,1) D2 region uniquely best among these cells;
vertical C leaves residual errors. There is no strict aggregate B-preference
reversal in this table. Useful-parameter constraints change without identifying
an intrinsic B price or requiring a rank reversal.
At D4 the horizontal best-tested set also includes B=1, but its minimum error
rises from0 to5/3. A wider relative-best region need not improve any fixed
quality threshold.

All 52 actual fresh-Core D2 trees independently reproduce 416 uniform-tie error checks,
762 visits in .546s. The corresponding literal full-history D4 calculation
uses 6,212 visits in .989s and includes 205 real repetition leaves. These are
reference costs, not public optimized-search nodes or a learner speed claim.

Deeper search does not preserve every previously safe score tie. At the
published selected horizontal root137, D2 uniquely selects a WIN action;
D4 gives that action and a DRAW alternative the same zero score. Its true WIN
rank is11. A 22-node all-defense strategy replays through the actual admitted
fresh rules. This explains a uniform-tie error increase, not a demonstrated
degradation of the deployed searcher's particular tie choice or whole-game
strength. No D6 expansion or price default follows.

One alternative learning explanation was checked without new search: among72
retained queries exactly at B=1,70 have nonterminal PVs and two have nonzero B
derivatives. None has a nonzero PV derivative masked by a locally constant full
D2 score, or a PV derivative outside its exact one-sided derivative interval.
This sample does not support degenerate-tie gradient masking as its failure
mechanism. It does not prove a general theorem about nested minimax ties.

## Extra board space: a separate finite control

The new 4x4 four-actor instance fixes K0 c1, axis actor0 c0, K1 a2, A1 b2.
The axis actor is called B by `make_rules`, rather than C by the earlier
coexistence constructor; unused type metadata also differs. No promotion,
drop or type-trigger law reads that metadata. The changed board gives a new
game and does not transplant a 3x3 played history.

Horizontal and vertical graphs complete 16,558 and 17,364 vertices, respectively,
in 41.350 combined seconds within 180 seconds/120,000 states each and 420 seconds
overall. Both roots and all four shared King actions are DRAW. The earlier 3x3
King c1-b0 liability is absent in this declared 4x4 control.

A literal horizontal line verifies why extra space can help:
`K0 c1-b0, A1 b2-b1, K0 b0-a0, K1 a2-b2, B0 c0-d0, A1 b1-a1, K0 a0-b0`.
The added d0 square lets the axis actor move without occupying the King's b0
escape. The line alone is not an optimal-policy proof; DRAW comes from the
complete graph. No monotone board-size law is inferred.

## Bounded first-passage follow-up

An explicitly idealized observer fixes A=1,B=3/4, uniform complete-D2 ties,
uniform legal random foe, the original eight prefixes/both colors, and 64
future plies. Its event is a different uniform-argmax WDL expectation at
B=1/4 versus3/4 on a learner turn. Oracle labels observe the event and never
change policy probabilities. Unexpanded path probability stays an exact
rational interval; no empirical zero is treated as impossibility.

The frozen allowance is 2,700 seconds/5,000,000 Core visits. Depth-first
enumeration spends much work on tiny-probability tails; its wide probability
gap is a cost limitation. The newly proved draw-only closure supports a separately
declared cheaper observer, not retroactive pruning or extension of this run.

The original pilot closes at2,700.002s,2,636,510 admitted visits and744,725
contexts,with probability bounds [0,.866184106]. The .002s cooperative overshoot
is not a chosen extension. Its TIME_CAP_UNKNOWN and incomplete mass are retained.

A new short control, with the same policy and original prefix/color mixture,
uses draw-only pruning and a frozen8-ply/600s/250,000-visit allowance. It fully
resolves3,831 contexts,17,903 visits in2.323s: the first8-ply event probability
is exactly0. This does not imply a64-ply zero. The separate pruned64 reference
stops at its1,000,000-visit allowance in63.892s, with225,511 contexts and exact
probability bounds [0,.816215745]. Its600s limit is not extended. Guard polling
also differs from the original pilot, so cost differences cannot be attributed
solely to graph pruning. Neither incomplete64-ply bound establishes rarity.
Because every allowed branch in the finite8-ply model has positive probability,
zero also means the declared event is absent from that entire8-ply support.
Changing only tie probabilities or foe probabilities within the same supports
cannot create this event there. This concerns the stated uniform-argmax WDL
contrast,not every possible notion of information, and assumes the same complete
D2 argmax supports;B=1 and incomplete-search policies are outside that claim.

A separately bounded breadth-first witness/control pass uses the same model,
draw-only pruning and120s/100,000-visit/10,000-frontier limits. It closes at the
node allowance in7.741s,15,334 contexts,no positive witness,with exact rational
probability bounds enclosed by **[0,.072736842]**. All64 root-by-trial mass sums
and common policy fields are checked. This is an upper bound for the declared
optimal-WDL event under an idealized policy,not an empirical frequency or a bound
for the deployed learner's arbitrary tie policy. Foe-specific return differences
can exist even when this event is absent. None of the earlier pilots is resumed
or extended. Better traversal,not a new rule executor,provides the useful bound.

## Validation and next decision

All175 related tests pass, including the two new closure regressions. Failed
observer attempts and the rejected fresh-initial witness remain local evidence.
No one-off drivers, full graphs or generated journals are added to Git.
Outgoing proof inputs are independently decoded and replayed:four positive roots,
all8,088 draw-only vertices/13,104 Core edges,and416 cached-versus-literal D4
error checks pass in19.675s/21,232 visits. Exact DRAW values remain graph-derived;
they are not mislabeled as finite positive certificates or outside-peer checks.

Next first examine whether the sole sampled equal-WDL boundary hides different
returns against the fixed random foe. Existing branches and the two observed
draw trajectories begin that inventory;no such counterfactual return observer
has launched. The low/high actions allow5/2 legal foe replies. Their worst-reply
material scores are -B and B-1,but their one-uniform-reply expected material
scores are -2B/5 and B-1:the proxy boundary shifts from1/2 to5/7. This is exact
saved-branch algebra,not a game-return measurement. Distinguish that estimand
before changing experience distributions
or evaluator features. Do not infer that
more wins, more parameter drift, broader opening count or higher search depth
automatically supplies that information. No oracle-guided experiential sampling,
old UNKNOWN extension, new worker or default change is authorized here.
