# C changes conditional strategic contributions

The strongest result is a small exact counterexample. At the same occupied
squares, replacing the second A on each side by horizontal C reverses which
of the original A and B is more costly to remove. Four finite WIN strategies
replay through actual Core; two DRAW values come from complete components.
All six positions also have legal six-ply prefixes whose complete-history
values agree with the fresh-history values. This establishes a conditional
ordinal contribution reversal. It does not identify unique material prices.

A separate parameter experiment illustrates why that distinction matters.
One D2 board has disjoint **uniform-tie-safe** B intervals between compositions,
yet the deployed search wins with the same high B in both. Setting C's leaf
weight to zero improves the ideal diagnostic and D2 decisions, but worsens
actual D4 decisions in the horizontal world. Every one of the 22,944 public
query actions still attains the true finite-depth maximum. These effects are
about the objective, depth and deterministic tie policy, rather than an
incorrect minimax result.

## Execution and rule scope

Shared infrastructure source: sandbox
`528c6d896e09c7f3c1008f09a07b04538ca20ef0`. Its terminal-aware quality changes
and tests were imported; all 238 shared package files match. The existing
learner, public iterative q0 search, Core and GameSession are reused. No new
engine, worker, model training or schedule change was made.
The closing fetch is `a552355e32a39fcff7d720d1181aebb904b79b79`; its additional
changes are PRIMARY research records, with no shared infrastructure delta.

The 3×3 rules have King-like Anchors, orthogonal A, King-like B, and either
horizontal or vertical C. Capture removes ordinary pieces. Core supplies
self-check legality, checkmate and stalemate; stalemate and second repetition
are draws. There are no drops, promotion, claims, rays or progress counters.
A conservative finite-position bound makes the required positive max-ply
clock inactive. Graph values concern fresh histories. Played prefixes receive
separate history-conditioned labels and actual Core checks.

ABA has two identical A pieces and one B per side. ABC replaces the second A
with C, preserving all eight occupied squares. The default layout, player 0
at the top, is:

```text
K0 A0 X0
B0  . B1
X1 A1 K1
```

Here X is the second A, horizontal C, or vertical C. Each new graph had its
own fixed 600-second / 300,000-position cap. No old experiment was resumed,
extended or filled.

| Component | Vertices | Edges | W / D / L, side to move | Initial player-0 result | Producer seconds |
|---|---:|---:|---|---|---:|
| ABA | 83,685 | 218,196 | 27,803 / 33,101 / 22,781 | WIN, rank 7 | 92.06 |
| ABC horizontal | 68,613 | 173,319 | 25,726 / 24,240 / 18,647 | LOSS, rank 8 | 75.34 |
| ABC vertical | 61,189 | 155,542 | 22,482 / 22,549 / 16,158 | WIN, rank 5 | 66.94 |

All graphs are complete. Every attractor/rank/residual constraint was checked.
Actual initial-root WIN certificates visit 14, 45 and 10 Core states,
respectively; the horizontal certificate proves the second player's win.
Elapsed costs include local output work and ordinary concurrent activity;
they are observations, not isolated performance comparisons.

## A/B contribution reverses when C changes

Consider this reachable position with player 0 to move:

```text
K0  . X0
A1  .  .
X1 B1 K1
```

The focal player is 1. A means the literal A at a1; B is at b2. X changes
between the two compositions. Removing a piece defines a fresh-history
state intervention. It is not an available move, an additive decomposition,
or a claim about what the same played game would do after deletion.

| Composition | Original | Remove A1 at a1 | Remove B1 at b2 |
|---|---|---|---|
| ABA | player 1 WIN | DRAW | player 1 WIN |
| ABC horizontal | player 1 WIN | player 1 WIN | DRAW |

This strict reversal survives every strictly increasing numerical encoding of
WIN/DRAW/LOSS: both original outcomes are WIN, and each composition has one
WIN-preserving deletion and one WIN-to-DRAW deletion. It is not created by
choosing a particular numeric WDL scale. B has all A's leaps plus diagonals;
the conditional contribution still follows the actor's actual square and
tactical role rather than the number of movement offsets.

With B removed, K0 can capture A1 at a1 in the horizontal world. It cannot do
so in ABA: X1 at a2 then has the vertical step that protects a1. Actual Core
checks this legality difference. The four non-draw cases have complete-history
WIN certificates of 3, 5, 3 and 5 states. All six shortest legal prefixes have
length six; their history-conditioned values agree with the table. The
prefixes differ, so they establish realizability rather than a matched
gameplay causal effect. DRAW comes from the complete graph and the separate
history observer, not a finite WIN certificate.

The selected panel contains two strict A/B deletion-order reversals. Across
2,854 individual deletion checks, 80 counterfactual labels are UNKNOWN because
their nonterminal boards are outside the relevant closed component. They are
retained. Counts describe this exposed panel, with correlated positions and
multiple interventions per position, rather than independent rule samples.

There are also non-monotone quantity examples. In one horizontal-C position,
the moving player's only legal move uses C, and the opponent has a seven-state
checked winning strategy. Removing that C immediately produces actual Core
stalemate, hence DRAW under these rules. Both boards have independently
replayed legal prefixes. C's presence is harmful in this specific state under
this terminal rule; no negative intrinsic price follows.

The separate C-deletion journal has 1,972 checks, one UNKNOWN and 346 events
where removing C improves its owner's ordinal WDL. A/B deletions supply ten
more such events. These are state-edit relations, not observed capture effects
or an average deployable material value.

## Matched boards and finite-depth parameters

For correspondence only, C is renamed A when matching an ABC board to ABA.
Side to move and every occupied coordinate are held fixed. Core fingerprints
remain bound to their own rules during execution; this correspondence is not
a shared transposition key or permission to reuse arbitrary history labels.

The three components share 37,209 ongoing matched boards: 31,040 without C,
5,804 with one C, and 365 with both C pieces. Only four common boards retain
all eight actors; only one is quiet with player 0 to move. Thus this crowded
default component is a narrow source of intact training starts.

The frozen panel uses 128 no-C boards, 256 one-C boards, and all 365 two-C
boards, in board-SHA order without WDL or parameter filtering. It includes
both players and mixed inventories/check states. Collapsing indistinguishable
A pieces yields 734 distinct ABA roots for the 749 matched interventions.
Their multiplicities are retained explicitly.

With A=C=1, all B leaf-order boundaries in [0,4] and their open-cell
representatives are covered by the 17 quarter-step values. The positive
region excludes the explicit B=0 boundary. Uniform ties mean uniform choice
among the exact depth-limited maximizing actions; deployed ties are measured
separately.

| Component, 749 matched rows | D2 ideal minimum errors | D4 ideal minimum errors | D4 minimizing positive B region |
|---|---:|---:|---|
| ABA | 51/2 | 0 | (2,4] |
| ABC horizontal | 353/10 | 21/2 | (3,4] |
| ABC vertical | 174/5 | 34/3 | (2,4] |

The aggregate minimizing regions overlap. They do not force a different
global B for each composition.

Actual iterative-search suboptimal actions, with complete D2 or D4 queries:

| Component | D2 B=1 | D2 transferred B | D2 B=3.5 | D4 B=1 | D4 transferred B | D4 B=3.5 |
|---|---:|---:|---:|---:|---:|---:|
| ABA | 50 | 26 | 26 | 9 | 0 | 0 |
| ABC horizontal | 59 | 38 | 38 | 12 | 8 | 7 |
| ABC vertical | 69 | 44 | 44 | 20 | 12 | 12 |

Transferred B is the previously frozen KAB TD result 2.4171096107122936.
B=3.5 is an explicitly oracle-selected diagnostic constant. There are 17,976
queries, zero missing slots and zero incomplete requested depths. All 1,024
no-C query pairs per ABC component match ABA in action, PV, nodes and WDL.

## A concrete price/tie mechanism

After the actual common first move A0 b0-b1, all three worlds reach the same
occupied board with player 1 to move. All have a player-1 WIN. Full-prefix
labels equal the separately checked fresh labels on this selected board;
this agreement is not assumed for other histories.

In ABA the unique D2 uniform-safe positive region is B>1. In horizontal ABC,
holding C=1, it is B<1. With high B the horizontal world ties a winning A
capture with a drawn B capture. The actual iterative policy chooses the WIN
in the checked high-B cases. Thus the disjoint **all-ties-safe** regions do not
establish an actual policy conflict. At D4 this panel has no such disjoint
pair. The actual common-prefix WIN certificates contain 10, 32 and 10 states.

For horizontal ABC, exact D2 scores in the moving player's orientation are:

| Action | Exact strategic WDL | Depth-2 material score |
|---|---|---|
| B captures C at c0 | DRAW | min(0,C-1) |
| B captures A at b1 | WIN | 1-B |
| B moves to b0 | LOSS | -B |
| A captures A at b1 | WIN | min(0,1-C) |

These expressions come from the full literal Core reply tree. In the bounded
positive parameter domain with terminal dominance, every maximizing action is
optimal exactly when B<1 or C<1. C=1 is a special tie boundary. Allowing a
different C can remove the ideal B conflict without adding representation.
This local fact does not optimize full-world play.

## C weight, depth and deterministic choice

For each C in {0,1/4,1/2,3/4,1,3/2,2,3,4}, all B leaf-order cells in (0,4]
were recomputed from the actual material forms. This is complete conditional
on those nine C values; it is not continuous joint B/C optimization. No oracle
fit or label was supplied to experiential training.

On the 621 C-present rows, ideal minima at C=1 versus C=0 are:

| Component | D2 C=1 → C=0 | D4 C=1 → C=0 |
|---|---|---|
| Horizontal | 487/15 → 129/5 | 21/2 → 15/2 |
| Vertical | 959/30 → 1469/60 | 34/3 → 25/3 |

C retains all its moves, attacks and terminal effects when its leaf weight is
zero. The zero-weight control is oracle-selected, not a learned model.
In 4,968 additional actual queries, with B frozen at the transferred value:

| Component | Actual D2 errors, C=1 → C=0 | Actual D4 errors, C=1 → C=0 |
|---|---|---|
| Horizontal | 35 → 25 | 8 → 10 |
| Vertical | 41 → 27 | 12 → 11 |

At one horizontal D4 root, the drawn and winning actions both score 1 with
either C weight. The C=0 PV/tie path selects DRAW; C=1 selects WIN. A portable
eight-state WIN certificate verifies the available winning continuation.
Across all 22,944 public root queries, independent cached-Core minimax and
54,230 literal legal PV moves confirm that the selected action attains the
true maximum and its PV reaches that value. The observed worsening is not
evidence that search returned a non-maximizing action.

The prior KAB panel also has a now-explained D2 regression at root 2453.
Uniform B=1 chooses WIN; transferred B chooses DRAW from the same maximum.
The effect needs both TT and ordering: disabling either removes it in the
selected ablation. D3 repairs it. There were 36 completed ablation queries,
and a ten-state actual WIN certificate. This is a selected mechanism, not an
argument to disable mainline TT/order defaults.

## Frozen transfer in actual games

No new learning was run. Each world uses its original single starting board,
32 new legal-RNG seeds, both colors, D2, and a 64-ply external fuse. C=1 is the
uniform new-feature weight. All 576 random-foe games and 12 deterministic
direct games reach actual rule terminals; no slot or UNKNOWN is omitted.

| World, 64 RNG games/model | Uniform W/D/L | Transferred W/D/L | Oracle constant W/D/L | Paired score gain, transfer minus uniform |
|---|---|---|---|---:|
| ABA | 34/30/0 | 58/6/0 | 58/6/0 | 3/16 |
| ABC horizontal | 33/29/2 | 48/16/0 | 48/16/0 | 17/128 |
| ABC vertical | 34/30/0 | 58/6/0 | 58/6/0 | 3/16 |

These are finite descriptive paired gains, not confidence intervals. Repeated
seeds on one layout are not independent position or rule replication. Coupled
RNG choices cease to coincide after different legal-action sets arise.
The transferred and oracle-constant arms have the same measured results;
no advantage over that cheap constant is established.

Transfer versus uniform direct play gives transfer one win/one draw in ABA,
one win/one loss in horizontal ABC, and one win/one draw in vertical ABC.
The horizontal outcomes follow its exact second-player advantage. The four
direct games per world are deterministic controls, not an Elo estimate.

Independent replay verifies all 588 records, 2,711 retained queries, 4,874 PV
moves and 2,377 RNG choices. Every retained query also receives its actual
complete-history action labels. Random-foe suboptimal-query counts are
45→0, 13→1 and 50→5 for uniform→transfer. Policy exposure differs, so these
counts are not causal per-query improvements.

## Does experience supply a C learning signal?

Retained frozen trajectories permit a local derivative diagnostic without
updating any parameter. Using the existing TDLeaf eta=.05, lambda=.95 and
scale=10, the forward eligibility sum and backward origin-credit sum agree
within 1.74e-18 across 384 horizontal/vertical random-foe records. These are
independent episode directions at a fixed model, not a sequential training
run, predicted endpoint or convergence result.

| Frozen policy | C-gradient origins / queries | Mean local C direction per game |
|---|---:|---:|
| Horizontal, uniform B | 81 / 382 | -0.000445536 |
| Horizontal, transferred B | 56 / 262 | -0.001803377 |
| Vertical, uniform B | 118 / 424 | +0.000509573 |
| Vertical, transferred B | 100 / 206 | -0.004591133 |

Thus the channel is not gradient-starved. Its local direction depends on the
frozen B policy and geometry/layout. The vertical uniform policy points toward
higher C even though the oracle grid favors lower C. This finite local
disagreement is not a prediction of an on-policy learning trajectory: B would
also change, and subsequent visited states/PVs would change.

In the transferred arms, all six observed suboptimal queries have zero
immediate C gradient. Earlier eligible gradients can still receive later TD
credit; zero gradient at an error is not a learning impossibility. Most net
negative C origin credit is outside the draw-only closure, so dead-state
calibration alone does not explain the direction.

There is a sharper local mechanism at the actual common-prefix witness.
For B=3 its root score is
`max(min(0,C-1), -2, -3, min(0,1-C)) = 0`.
The entire depth-2 value envelope is flat, including at C=1. Reusing the
closed C=1 query and issuing just two new epsilon queries gives:

| C | Actual chosen WDL | Player-0 PV value | Literal C leaf gradient |
|---|---|---:|---:|
| .999 | WIN for moving player 1 | 0 | 0 |
| 1 | WIN for moving player 1 | 0 | +.1 |
| 1.001 | DRAW | 0 | 0 |

At C=1 the retained leaf feature is `A=-1,B=0,C=1`; the balanced leaf chosen
on either side has all features zero. Thus the retained-leaf TD gradient is
not the derivative of the flat max-min envelope at this tie. The changed PV
and action are legal exact maxima. This is a concrete semi-gradient/selection
mechanism, not a search bug or proof that a subsequent TD update is harmful.
The same exact local-envelope check covers all 511 nonzero C-gradient origins
in these retained records. Flat value with nonzero literal-PV gradient occurs
in 40/81 horizontal-uniform origins, 8/56 horizontal-transfer origins and
8/56 horizontal-oracle-constant origins. It occurs in none of the vertical
origins (118/100/100). All 56 flat cases also change ideal maximizing sets
across the tie. These are exposure-weighted, correlated counts; actual WDL
change is established separately for the selected witness.

A separate label-blind feasibility batch freezes 128 legal random opening
walks per world, target lengths cycling 1–6. Each has 11 terminal prefixes;
duplicates and terminals remain. The 128 observations represent 80 and 83
distinct actual histories. Of 117 ongoing prefixes, 54 horizontal and 65
vertical have actions with different exact WDL. The C=1 policy has a nonzero C
gradient in 35 and 46 queries. Changing only C to zero changes chosen WDL in
four horizontal prefixes and zero vertical prefixes; errors are 6→2 and
11→11. All 468 requested queries complete. This is a feasible future experience
protocol, not oracle-filtered training data or an independent validation set.

## Semantic controls, failures and retained limits

* Every horizontal-component vertex/edge is independently checked through
  vertical Core after a 90-degree rotation: 68,613 vertices and 173,319 edges.
  Thus H and V are isomorphic geometries with different original layouts.
  Their fixed-layout differences are geometry-by-layout effects.
* All 35,144 states and 93,024 transitions of the old KAB component form a
  matching closed subset after C is absent. H and V also reach 32 and 14
  additional no-C states. The first strict whole-set-equality check failed;
  the corrected intersection check retains those extras rather than calling
  them old missing slots or draws.
* The correctly keyed frozen-policy geometry control executes 2,048 queries
  on the original 128 boards. Eleven diagonal boards lack saved component
  labels: 88 query labels stay UNKNOWN despite complete searches. The 42
  owner-swapped bindings are backed by full actual-Core validation of the
  22,660-state / 59,528-edge diagonal component. The old 126/128 training-order
  error is preserved; no training or missing-label solve was repeated.
* The initial attempt to declare a checked moving Anchor as a schema initial
  setup was rejected. Core fresh-state analysis and schema initial admission
  are different contracts. The selected reversal now has legal actual prefixes
  and separately checked history values; no rejected setup is called admitted.
* An early one-off arithmetic grid ignored one V checkmate leaf. Its original
  output is retained and excluded. All 60 corrected score vectors match the
  authoritative cached-Core D2 calculation. Graphs, actual public queries and
  WIN certificates were unaffected. An earlier fingerprint assertion and its
  local repair are also retained; they produced no successful query data.
  The opening probe's first attribute check also failed before any query;
  repair reused its frozen paths and charged the original allowance.
* The C deletion branch initially had only summary output; its 1,972 raw rows
  were explicitly reconstructed from retained graphs/Core, including UNKNOWN.
  No new game, graph, exposed holdout or old cap was manufactured.

The old setup-order failure, 65 earlier UNKNOWN games and 394 unprocessed
historical oracle queries remain unchanged. Current results are component-,
history-, distribution-, opponent-, depth- and tie-policy-specific.
The 124 relevant learning/runtime, Leaper and terminal-aware quality tests pass.
The local JUnit file remains private because it includes machine metadata.

## Reproduction and next decision

The existing public helpers suffice to rebuild each new graph:

```python
from scripts.leaper_microgames import KING
from scripts.leaper_retrograde import solve_world
g = solve_world(lineup=('A','B','C'), b_geometry=KING,
    composition_c_axis='horizontal', seconds=600, max_states=300000)
```

Use lineup `('A','B','A')` for ABA and axis `vertical` for V. Graph construction
sorts literal actions. Match `(side_to_move, owner/type board)` after the
declared C→A rename; SHA-sort the JSON encoding with compact separators before
selecting 128/256/all rows by C count. `root_action_labels`, `decision_relevance`,
`action_scores`, `history_value` and `winning_history_certificate` are the
existing observers. The public search receives the actual GameSession history.

The compact companion JSON contains fixed configurations, summary tables,
selected literal Core trees, legal prefixes and portable WIN strategies.
Raw complete graphs, journals and one-off analysis drivers remain in ignored
local artifacts. The compact file does not reconstruct every private journal.
Independent verification of the actual outgoing JSON replays all 16 stored
WIN certificates, the selected literal D2 branches and the C0/C1 D4 scores
through Core (366 visits). Graph DRAW claims retain their explicit source.

The next useful experiment is a bounded horizontal-C learning comparison from
uniform versus transferred B, with C=1, using the frozen label-blind opening
protocol and the same learner. A balanced 512 episodes means two trials of
128 openings in both colors. Existing per-arm 120-second / 2,000,000-node
allowances, actual terminals, missing slots and oracle exclusion remain.
It has not been launched. The benchmark shows why prediction or ideal-tie
improvement must be checked against the actual depth-specific policy.
