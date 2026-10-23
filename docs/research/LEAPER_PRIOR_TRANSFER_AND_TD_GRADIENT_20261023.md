# ABC prior transfer and a zero-gradient TDLeaf counterexample

DEV_AUX / sidemission. PRIMARY owns rule generation, opening design, forward
screening and label-cycle work. This study consumes its frozen rules and full
histories through the committed Core, GameSession and public search. No engine,
evaluator, learner default or other-role state changes.

## Decision

On the newer ABC contexts, the previously selected B=2, C=1 price and both free
priors produce exactly the same paired terminal outcomes as Unit. Different
search supports and trajectories therefore do not establish a learning benefit.
No online TD run or game played by updated weights was launched.

A separate missing-control experiment adds mobility and Static-material to the
older ABC cohort where B2C1 had shown a positive finite gain. It reuses the
completed Unit/B2C1 results without repeating or extending their closed runs.
They explain most of the earlier gain; the remaining advantage is two same-role conversions, qualified below.

## Shared infrastructure and fair-comparison scope

The recovery source is sandbox `bf725532ea38deb5242538575c4065a63615b8c2`.
Relative to the preceding `ff72649685c21a37bdbe147c930e4b2070934f77`, this commit
adds research results only. Rules, Core, Session, search and public Leaper helpers
match the committed mainline. The package retains only the maintained AUX learner
and receipt adapter differences. This is infrastructure reuse, not a speed claim.

Every new policy call uses `generic_chess.learning.mainline_search.search`:
completed D4, 8192 nodes, two seconds including literal PV replay, q0, fresh TT per
query and equal capture ordering. The candidate changes only leaf material prices,
with A fixed to one and inactive hand channels zero. The common opponent uses
actual empty-board mobility ratios under the same interface and D4 limits.
Rule repetition 4, rule max_ply 128 and the caller's absolute 128-ply cap are distinct.
An incomplete query would remain UNKNOWN and advance no action.

These AUX leaf controls differ from PRIMARY's full dynamic Static/M0 and retained
per-game TT screen. The two experiments are not interchangeable evidence.

## Newer contexts: all 512 slots close without a price benefit

Inputs are the four original FIRST3/4 worlds in PRIMARY's committed packet:
two layouts each for exposed physical codes `(9,9,8)` and `(10,19,8)`.
The existing law draws up to eight uniformly sampled legal plies, stopping only at
a real terminal. Seed 830427 fixes 16 prefixes per world. All 64 complete histories
are distinct; ten are already terminal. No oracle, price-response or outcome
filter chooses starts. Every price and both candidate roles share each prefix.

The four priors have A=1:

| Code | Unit B,C | B2C1 | Mobility B,C | Static-material B,C |
|---|---|---|---|---|
| `(9,9,8)` |1,1|2,1|1,1/2|1,0.515|
| `(10,19,8)` |1,1|2,1|25/21,4/7|1.184,0.586|

All 512 slots complete:432 controller continuations plus 80 terminal-prefix views.
There are 80 distinct final GameRecords. Actual cost is 21,700 D4 queries,
4,462,768 nodes and 1471.730 seconds. The cold natural-prefix pilot costs 20.070
seconds for 56 nonterminal root calls plus eight games; its outcomes are excluded.

| Prior | W/D/L over128 | Mean utility | Difference from Unit |
|---|---|---|---|
| Unit |39/50/39|0|0|
| B2C1 |39/50/39|0|0|
| Mobility |39/50/39|0|0|
| Static-material |39/50/39|0|0|

This is stronger than equality of aggregate means: **every matched world,
prefix and role has the same terminal outcome across all four prices**.
For each price, role 0 has mean−7/64 and role 1 has+7/64; every world mean is zero.
There are zero UNKNOWN slots. Terminal-prefix views and dependent deterministic
records remain in the denominator;512 is not an independent-sample count.

The result is a finite transfer failure of the older selected price, not a
confidence interval, price-family ceiling, intrinsic-price statement or proof
that TD cannot help elsewhere. In particular, `(9,9,8)` gives A and B identical
movement; assigning them unequal constants does not identify distinct intrinsic
values.

## Actual first divergences and the derivative issue

All 384 non-Unit/Unit paired frames are inventoried before looking at supports:
353 have identical complete records and 31 first diverge at 16 distinct full
histories. All 31 still have zero paired final-utility difference.

Literal full-history Core D4 trees complete at all 16 roots:32,061 visits,
13.604 seconds. Twenty-seven paired controls change the complete optimal support;
four keep both served actions co-optimal under both prices. Actual float supports
equal the exact-binary-parameter rational supports in every checked control.
No float rounding defect is needed to explain the paths.

For Unit and B2C1, each leaf's free B/C gradient lies in `{-1,0,1}²`.
Sixteen open cones separate every possible distinct gradient. Propagating a
primary score and a secondary directional slope through the complete tree gives
the limiting affine gradient in each cone. The convex hull of these limiting
gradients is the local Clarke set for this finite piecewise-affine critic.
This diagnostic does not replace the learner or its search.

One of these 16 exposed first-divergence roots has a selected Unit PV derivative
outside that set:

`e869b41e04e44772b9c029c1484e294b5ee31810cbb894c059ec1cdbe81e3bc5`

It is world 1, prefix 10, candidate role 1, absolute ply19. In neighborhoods of
both `(B,C)=(1,1)` and `(2,1)`, the player0 D4 critic is exactly `C−1`.
The limiting raw B/C gradient is uniquely `(0,1)`. At either original point,
the served PV ends in a real rule draw and supplies gradient `(0,0)`.
Thus even a differentiable root critic can have a selected tied leaf whose
derivative is not its derivative. B2C1 is nonuniform yet retains this tie.

The local boxes satisfy `|B−B0|,|C−1|<1/4`. Non-through-base leaf gaps are
integers of magnitude at least one, while leaf-gradient differences have L1 norm
at most four. No other leaf-order plane crosses those boxes. All open cones have
the same gradient, and continuity joins their affine pieces. Sixty-four NEW public
D4 calls use two dyadic step sizes and all 16 directions around both bases.
Every value exactly equals `C−1`, every perturbed PV has B/C gradient `(0,1)`;
14,752 nodes,4.172 seconds. Both original base receipts are reused, not searched
again. This is a local critic result, not a game-value or strength result.

The root has prehistory count 3. A NEW complete component has 48,120 states and
253,160 edges, built in 72.155 seconds. Every root action has fresh graph DRAW;
extra actual draw stops cannot create a decisive win, so all eight actions are
also DRAW under this full history. The root is outside the structural draw-only
closure: cooperative mate remains reachable. Neither the gradient anomaly nor
the changed supports demonstrate a minimax action-quality benefit here.

[Baxter, Tridgell and Weaver, section4](https://arxiv.org/pdf/cs/9901001)
discuss arbitrary leaf selection at minimax ties. The observed derivative is
therefore described as a tie-dependent surrogate, without declaring TDLeaf a
search-value bug or a generally unsuccessful learner. Averaging all tied PV
derivatives is not a universal correction either: for
`max(min(0,x),min(0,−x),min(0,y))=0`, the unique co-optimal leaf slopes include
`0,+ex,−ex,+ey`; their mean `(0,1/4)` lies outside the true Clarke set `{0}`.
Four closed-form positive/negative controls qualify the finite-cone calculation.

## New natural-history truth, with missing coverage retained

Before any new graph labels, metadata hashes choose one ongoing four-actor
history per original world from all committed original-encoding common-opponent
trajectories. The source has 171 references and 133 distinct histories.
All four new 90-second/101,280-state components close inside the 480-second budget:
195,468 summed entries,981,952 edges,293.241 seconds. These are paid entries
across components, not unique independent game states. The old five-actor cap
remains closed.

Of the 133 source histories,36 receive exact action labels and 97 remain uncovered.
Intersecting the new prior games with those components gives3367 distinct queried
capture-reduced histories:1068 exact,338 bounded and 1961 uncovered. Saturated
nonzero history values remain one-sided; they are never filled as draws.
Among candidate-owned decisions, exact histories number 808 for Unit,852 for
B2C1 and 919 each for mobility and Static. No covered selected action is certified
strictly worse, while bounded and uncovered actions remain unresolved.
Different policies visit different histories, so these counts are not a paired
error-rate efficacy estimate.

The first intersection reader used PRIMARY's action serialization matcher on AUX
serialized query actions and failed. A reader-only fix uses the actual action
dictionary schema; the failure and its7.215 seconds are retained. No game, query,
graph or old cap is rerun to repair that representation error.

## Missing free-prior controls on the older positive cohort

This is a NEW bounded addition to the already completed older validation cohort,
not further validation or another selected price grid. It keeps the same eight
55ab ABC worlds, all 64 frozen prefixes, both roles, fixed mobility opponent and
literal D4 resource conditions. Unit/B2C1's256 completed results remain unchanged.
Only mobility and Static-material add256 new slots, with an 1800-second cap and
a 1200-second estimate based on the old 1115.322-second run. No missing old slot,
old model or old budget is resumed.

All 256 NEW slots close:248 continuations plus eight terminal-prefix views,
19,796 completed D4 queries,3,791,630 nodes and 1169.204 seconds. The four-price
comparison below includes256 unchanged old Unit/B2C1 views; it is not512 new games.

| Prior | W/D/L over128 | Utility | Versus Unit | Versus free priors |
|---|---|---|---|---|
| Unit, reused |9/105/14|−5/128|0|−5/128|
| B2C1, reused |14/102/12|1/64|7/128|1/64|
| Mobility, new |12/104/12|0|5/128|0|
| Static-material, new |12/104/12|0|5/128|0|

The two free priors have identical complete records in every matched frame.
Their 256 slots share64 distinct final records; repeated deterministic role views
are counted as paid computation, not independent information. Unit matches their
outcome in 123/128 frames and is worse in five. B2C1 matches in 126/128 and converts
two draws to wins, both role 0: world 4/prefix 4 and world 10/prefix 1. Its role 0 gain
versus the free priors is 1/32; role 1 gain is zero. Thus5/128 of the earlier7/128
contrast is already available without training; the remaining1/64 is a small,
exposed conditional effect, not a robust population or intrinsic-price result.

Only these two residual frames receive a new mechanism follow-up. Their first
shared-history divergences have six actors, at plies10 and 22; the latter has
prehistory count3. Neither lies in an old complete four-actor component. Four
literal D4/D6 trees complete in 16.277 seconds,183,270 visits. At world 4, B2C1's
D4 support excludes the mobility-served action, while mobility keeps both actual
actions co-optimal. At world 10, B2C1 keeps both actions co-optimal, while mobility
excludes the B2C1-served action. D6 retains these distinctions. Every tested action
still has conservative true-WDL bounds [−1,1]; no finite cutoff becomes a draw.

Four NEW continuations then force the other policy's first action and retain a
fixed later candidate policy and the same mobility opponent. Original outcomes
are reused; the new work pays264 D4 queries,44,644 nodes and 16.171 seconds,
zero UNKNOWN. All utilities below are for the same role 0 candidate.

| Case | B2 first/B2 tail, reused | Mobility first/B2 tail, new | B2 first/Mobility tail, new | Mobility first/Mobility tail, reused |
|---|---|---|---|---|
| world 4/prefix 4 |WIN|DRAW|DRAW|DRAW|
| world 10/prefix 1 |WIN|DRAW|WIN|DRAW|

In world 4, the first B2C1 action is necessary but insufficient under these fixed
policies: its later policy also matters. In world 10, the first changed action
alone suffices against this opponent; it is a B2C1 co-optimal tie choice.
These are conditional policy interventions, not exact action-WDL labels or a
claim that an arbitrary tie override should become a production default.

The next useful step has begun with detached TDLeaf arithmetic on the 256 actual
frozen-policy Unit/mobility trajectories. There are 9803 own-actor targets,
7119 nonzero B/C gradients and 178 nonzero episode deltas. One mean episode
update per world/initialization uses eta 0.05, lambda 0.95, scale 10, actual terminal
rewards and the maintained library. No oracle label chooses a training start.
Sixteen metadata-selected first-own-query roots receive16 NEW D4 queries under
the shadow endpoints, reusing all 16 original base receipts:3525 nodes,0.942s,
two changed actions. This is neither updated-policy play nor a strength result.
The public packet marks the mean-update arithmetic as reported preparation;
its32 query PVs are replayable, while complete target-stream binding remains
in the hashed private full receipts. A prospective six-policy384-slot pilot
would project1753.806 seconds from the new measured control cost, with a proposed
2400-second cap. It has not started; changing policies can change that cost.

The new producer inherits a stale selection-description string mentioning the
newer four-world sampling mode. Its actual input bytes, source code, explicit
interpretation and prefix-law replay bind these eight older worlds and reused
prefixes. This is a prose qualification, not an alteration of executed inputs.

## Evidence and checks

Curated JSON-only packets and portable readers are in
[the evidence directory](data/leaper_prior_controls_20261023/README.md).
Full graphs, raw query ledgers and temporary drivers remain ignored.
The new-context full private replay passes all 21,700 queries and 84,325 PV edges.
The public projection independently replays all 512 outcomes and 64 prefix draws,
plus 653 metadata-selected query examples and 2533 PV edges.
The mechanism reader independently recovers all 16 tangent regions using two
integer dyadic points per cone, checks1024 such points and all 66 public/reused
PV receipts, in 3.683 seconds. Public and private query scopes remain distinct.

The added-control full private reader checks all 19,796 queries and 77,700 PV
edges in 39.392 seconds. The public combined reader replays every new control
outcome,1067 selected queries/4172 PV edges and all 256 reused baseline outcomes,
then recomputes the four-price contrasts and complete-record matches.
The truth reader rebuilds only the five NEW components through Core:
243,588 summed entries/1,235,112 edges,133 source and 3367 queried histories,
including the count3 counterexample. PASS in 546.487 seconds. It reconstructs all
repeated512-slot decision references from complete records instead of publishing
19,659 repeated observation rows. These checks share Core; they do not certify
physical CPU work or prove a general history quotient. The 87 relevant Leaper/public-learner compatibility tests pass in 3.52 seconds.
No broader product test sweep is repeated.

The user's latest explicit cadence change updates the two existing patrols to
120 minutes, read back ACTIVE with their original chats. It does not change
the 60–90-minute effective-work requirement. Configuration time is excluded;
no Agent, worker, Goal, new timer, Slack resend or other-role research write is
created. Research remains open beyond these bounded questions.
