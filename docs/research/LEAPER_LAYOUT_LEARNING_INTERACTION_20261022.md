# Leaper layout, learning and conditional contribution

DEV_AUX, 2026-10-22 JST. Infrastructure source:
`07b4b4a24167b0643bdd892e7d2914adc3c5e120` on sandbox. All 238 shared package
files have identical Git content; 237 have only Windows line-ending differences
in their working bytes. The two existing AUX learner modules remain additional.
The newly committed semantic cost-probe caller and its regression tests were
imported. Core, rules, GameSession, terminal/history and public search are reused.
Numerical evidence is in [the compact data](data/leaper_layout_learning_interaction_20261022.json).

The strongest new result is an exact conditional-contribution sign reversal.
At fixed squares, C helps its owner when A is present and harms it when A is
absent. Four separately compiled, legal fresh games establish this result.
Learning also produces some better choices, with explicit limits below.

## One layout intervention

The declared intervention swaps squares 1/3 and 7/5 in BOTH ABA and ABC. Extra
actor squares, owners, inventory and occupancy stay fixed. It changes the
initial placement of A/B, not their movement or the searcher. The new starts
have 4/3 legal actions, safe Anchors, and are not D4 copies of the old boards.

The same selection procedure finds 458 common ongoing H6 prefixes in this
layout. They are replayed with full history under the inactive-clock rule.
This distribution differs from the old layout's 186 prefixes. Consequently
cross-layout differences include the distribution induced by the layout;
they are not a fixed-context causal estimate or independent rule samples.

All 7,328 planned public q0 queries complete the requested depth, with zero
missing/UNKNOWN: 488,859 nodes, 405.12 seconds including exact graph generation.
Each query has 100,000 nodes/3 seconds; the unchanged whole budget is 600 seconds.

| World | B, with A=C=1 | D1 errors | D2 | D3 | D6 |
|---|---:|---:|---:|---:|---:|
| ABA | .25 | 30 | 18 | 8 | 0 |
| ABA | 3 | 34 | 20 | 11 | 0 |
| ABC | .25 | 44 | 35 | 22 | 11 |
| ABC | 3 | 44 | 36 | 23 | 14 |

Both fresh roots draw. Complete ABA/ABC graphs have 57,800/48,365 Positions,
160,550/129,171 edges and maximum decisive distances 8/17. Exact labels change
from H6 at 35/84 compared prefixes. The previous D1 contrast, ABA preferring
low B and ABC high B, does not survive: ABC now ties. Six ABC prefixes improve
and six worsen when B goes from .25 to 3. No individual common prefix has
strictly opposite signed effects between ABA and ABC.

## Price errors and ties

A zero-new-search analysis scores every legal D1 action at all 1,288 existing
world/history contexts across both layouts. Full-prefix exact labels and all
2,576 saved endpoint choices agree with the corresponding material-optimal
action sets. Within 0<B<8, A=C=1, leaf-order boundaries are B=1 in the original
layout and B=1,2 in the swapped layout. Boundaries are treated separately.

| Context family | Low B forced errors / unsafe ties | High B forced errors / unsafe ties |
|---|---:|---:|
| Original ABA | 4 / 9 | 6 / 16 |
| Original ABC | 20 / 12 | 13 / 19 |
| Swapped ABA | 11 / 42 | 14 / 44 |
| Swapped ABC | 27 / 37 | 26 / 39 |

A forced error means every material-best action has suboptimal exact WDL.
An unsafe tie mixes optimal and suboptimal WDL. The actual deterministic choice
need not realize every tie risk, so these columns must not be added to claim
an observed error count.

More strongly, 7/10/30/19 contexts respectively give EVERY D1 successor the
same complete material vector, or the same actual draw-zero value, while WDL
differs. All material coefficients leave those successors tied. This includes
C as a free coefficient; one additional swapped ABC tie is only B-invariant.
Deeper public search resolves several examples. This is a finite representation
limit, not a demand to replace the material learner or modify the mainline engine.

## Experiential learning beyond two deterministic trajectories

Eight opening prefixes were fixed using RNG seed 20261022 and uniformly legal
moves; target lengths cycle 1 through 6. Terminals and duplicates are retained,
with no oracle/search selection. There are seven distinct prefixes. Full history
is replayed; no Position reset occurs. The existing episode-frozen TDLeaf uses
A=1, uniform other weights, scale 10, eta .05, lambda .95, D2 q0 and a uniform
D2 opponent. Each prefix receives both learner colors, twice, for 32 episodes.
Budget: 120 seconds/2M nodes overall, 64 plies/524,288 nodes/10 seconds per game.

All 32 games reach actual draws: 400 queries, 4,452 nodes, 3.33 seconds and 14
changing updates. Final B=.9900874213, C=.9659358144. Independently replaying
all records and 400 literal PVs, and recomputing all 198 forward TD terms,
finds zero discrepancy. There are 102 distinct experienced contexts.

At the learner's 198 actual choices, its episode-frozen weights make 10 WDL
errors; matched initial-weight queries make 22. Sixteen moves differ: twelve
strictly improve exact WDL and four preserve it. None worsens. These are
post-hoc, repeated, treatment-exposed histories, not an independent strength test.

The frozen final model is also queried on the already exposed ABC benchmark:

| Layout | Histories | Initial D2 errors | Final D2 errors | Better / worse WDL |
|---|---:|---:|---:|---:|
| Original | 186 | 21 | 16 | 5 / 0 |
| Swapped | 458 | 34 | 25 | 10 / 1 |

All 1,288 endpoint rows are present and complete. The 186 original initial
queries were reused, not rerun; other parameter queries are new. This supports
conditional action-quality improvement beyond the training trajectory, including
one regression. The benchmark was already exposed before training; no population,
held-out or universal-transfer claim follows.

A second, separately bounded 32-episode mechanism control keeps these openings
and learner fixed and replaces only the training foe by uniform legal moves
with fixed RNG seeds 2026102201+episode. Random moves have no fabricated search
receipt or node charge. Actual record/ply/query accounting is regression-tested.
It again yields 32 actual draws, 27 updates, 324 learner searches/3,817 nodes,
2.97 seconds, and B=.9759343935, C=.9344513766. It supplies no additional terminal
W/L signal in this sample. Independent full replay checks all 32 records, 324
literal PVs/forward TD terms and 325 exact RNG replies, with zero discrepancy.
The D2-foe draws are all repetitions; random-foe draws are 30 repetitions and
two stalemates. None is a search/horizon UNKNOWN assigned a draw.

Despite this larger parameter drift, BOTH learned vectors order all 27 possible
ABC material vectors identically: all 351 pair comparisons agree. Their common
open cell is specified in the data by six affine inequalities. Min/max search
with these unchanged terminal-distance values therefore has the same optimal
action SETS at any complete q0 depth. Numeric targets and gradients may differ.
An actual public D2 check at all 644 exposed histories confirms identical
actions AND nodes, with no missing/incomplete query. No behavioral improvement
from this extra drift is established.

## A draw opponent can hide an exploitable policy

A bounded all-opponent-response unroll attempted 32 frozen-policy cases, using
the existing Core reference with one player's public D2 choices fixed. It
closed partially: nine exact DRAW proofs, sixteen budget UNKNOWNs, one harness
failure, one cancelled case, and five never-started cases. The failure was a
deadline race yielding an invalid negative search budget. Its slot was retained;
only never-started slots resumed within the original 1,000-second deadline.
No cap or failed slot was reset. Logged work is 43,200 searches/383,498 nodes;
one in-flight cancelled query may add up to 8,192 unlogged nodes.

A cheaper separate post-hoc witness made further unrolling unnecessary. At
opening 7, learner color 1, the opponent supplies one legal first reply. Both
initial and final D2 models then choose B (1,2)->(0,1), although a drawing action
exists. Actual Core validates an opponent win at rank 7 against ALL subsequent
defenses: eight nodes, one checkmate branch. There is no earlier learner move
after this opening, so the witness applies directly to each frozen endpoint.
It is not inserted into capped/missing unroll slots. The optional unroll hook
was removed from maintained code; exact executed sources and partial traces
remain private. Pointwise gains and 32 observed draws do not certify robustness.

## Exact A–C contribution reversal

Post-hoc removal pairs in the cached ABC graphs show that C's presence can help,
harm or leave fresh WDL unchanged. The original layout contains 28,716 matched
presence/removal pairs, including 4,526 harmful cases; the swapped layout has
32,707 pairs, including 4,947 harmful cases. These overlapping graph counts are
not a sampled distribution from which an intrinsic negative C price is estimated.

Removing own A and/or C gives four-state comparisons. Original/swapped graphs
contain 16,882/20,330 such cases, including 130/150 strict signs of C's marginal
contribution reversing with A. In 71/86 cases all FOUR states are ongoing.
Fresh histories are specified separately; played-history values are not replaced
by these Position labels. Removing actors deliberately changes occupancy and
inventory, whereas the preceding ABA/ABC replacement held both fixed.

One selected all-ongoing case was independently made into four public fresh
games. All have player 0 to move, safe Anchors, the same movement/terminal laws
and inactive clock. Fixed actors are K0 at 0, B0 at 3, A0 at 4, K1 at 8.
Optional owner-1 actors are A1 at 5 and C1 at 6. Squares are row-major on 3x3.

| Owner-1 inventory | Reachable Positions | Edges | Owner-1 exact value |
|---|---:|---:|---|
| A+C | 12,854 | 32,933 | DRAW |
| A | 7,128 | 18,360 | LOSS, mate in 1 |
| C | 1,958 | 4,232 | LOSS, mate in 3 |
| Neither | 531 | 1,101 | DRAW |

The four distinct fingerprints bind real GameSession fresh roots. Total solve
time is 23.16 seconds, within 120 seconds/200k Positions per graph and 600 seconds
jointly. Complete action, edge, terminal, value and rank correspondence with the
old graph is checked at ALL 22,471 vertices/56,626 edges after fingerprint
renaming. These counts include overlapping components. Winning cases have
actual all-defense Core rank certificates.

Thus C contributes +1 with A and -1 without A. The mixed difference is +2.
The signs persist under any strictly increasing utility convention separating
draw and loss. A monotone transform of a context-independent additive material
sum cannot rank both diagonal DRAW cases above the two off-diagonal LOSS cases.
This is a counterexample to that strategic-value representation, not a statement
that a fixed coefficient is useless inside search.

The geometry gives a short explanation. With A alone, A0 (1,1)->(1,2) mates;
friendly A1 blocks K1's escape and C1 is absent. With A+C, C1 can capture that
checking A0 and draw. With C alone, K0 (0,0)->(1,0) is a winning wait: C1's only
reply is (0,2)->(1,2), then A0 captures it at (1,2) and mates. Without either
unit, that wait instead immediately stalemates K1 and draws. With both units,
A1 can capture A0 at (1,1) after the wait and draw; moving C instead loses.

Uniform-material public D1/D2/D3 already chooses optimal WDL at all four roots
(12 complete queries). C-only has six identical D1 material successors, three
winning and three drawing; the actual D1 tie choice happens to win. D3 exports
a literal mate PV. This small example isolates contribution and cooperation;
it is not by itself a discriminating strength benchmark or a reason to train
an interaction coefficient. Greater depth can use existing rule geometry.

Changing ONLY stalemate from draw to side-to-move loss changes the owner-1
matrix to [DRAW, LOSS, LOSS, LOSS]. Core terminal status/winner is checked at
every vertex before cached physical edges are revalued. All decisive roots
again have actual full-defense certificates. C's contribution becomes +1 with
A and 0 without A: the negative branch disappears, while interaction remains.
This is a new rule control; all old draw-policy results are preserved.

A final single geometry control rotates ONLY C's two steps from horizontal to
vertical, keeping the same four physical starts and stalemate-draw law. All
four fresh graphs complete in 22.41 seconds, within the separately declared
120-second/200k per-world and 600-second joint limits. Owner-1 values become
[LOSS, LOSS, LOSS, DRAW]: C's contribution is now 0 with A and -1 without A.
The horizontal defensive capture of A0 at (1,2) has disappeared; A+C now loses
to immediate mate. The two C-absent components are rechecked controls, not
additional samples. Geometry removes the positive branch, while the preceding
stalemate intervention removes the negative branch. Neither intervention
justifies assigning an intrinsic price.

The smaller `conditional_C_liability()` witness also replays two actual legal
histories of the SAME symmetric rule. Their physical boards differ only by C0:
its presence leaves one forced move followed by mate; its absence stalemates.
Their distinct histories are explicit. Compiler rejections of unequal-inventory
setup options and already-terminal initial positions were respected; no mainline
validation was bypassed and no alternate engine was written.

## Reusing task2620 without new games

Selected exact members of the capsule at historical
`e6368f3c67ad386d5f10dac81355175cc05a4abf` were verified against their manifest.
All 1,536 game records and 222,704 query rows were read; 1,267 actual terminals,
269 UNKNOWN and zero missing remain unchanged. No training/search was rerun.

Its ordering seed formula excludes the endpoint. Every query matches that
formula, with zero mismatch. Across all six endpoint contrasts, every first
actual move divergence occurs at the candidate, never the fixed foe. For
TDLeaf versus initial there are 368 candidate-first divergences, 15 identical
trajectories and one prefix-censoring case; one first divergence has different
remaining node requests. This does not inherit task2625's endpoint-seed defect.
Later shared-slot resource depletion can still couple the foe's available
computation to candidate search cost. Post-selected divergence groups are not
new causal populations. The original six finite-panel bounds, including
TDLeaf-minus-initial [29/384,111/128], retain their original interpretation.

## Delivery and next question

142 relevant regressions pass. Large generated traces, graphs, partial failures
and source copies remain ignored; maintained code, concise findings and compact
numeric evidence are published. No new Agent, worker, Goal, timer, other-role
write, visibility change, old cap reset or UNKNOWN imputation occurs. Existing
ACTIVE 90-minute recurrence and stops remain. Slack advice was read and adopted
with limits; the old uncertain report was not resent.

The next policy question is whether the geometry change also changes useful
frozen coefficients at identical legal histories. Preparation has begun: the
C-only horizontal/vertical H6 trees have 407/314 contexts and 85 common ongoing
prefixes. Every prefix replays under both inactive-clock rules with full history.
Their actual-history WDL and initial-versus-learned policy comparisons have NOT
been computed. The proposed bounded study reuses both graph caches and any
already-saved identical root queries; it compares uniform and the frozen D2-foe
final model at D1/D2/D3, within 600 seconds. No new training or architecture is
needed, and closed unroll/learning slots remain closed.

Reproduction uses fresh output directories and the maintained constructors:
`coexistence_rules(..., layout='swap_ab')`, `composition_without_clock(...,
layout='swap_ab', ratios=(.25,3.))`, `experiential_probe(..., opening_count=8)`,
and its explicit `random_foe_seed=2026102201` control. The four-game actors above
pass through `solve_world(lineup=('A','B','C'), initial_position=board)`.
`conditional_C_liability()` returns a fully replayable small witness. These
entries reproduce methods; they do not authorize refilling closed runs.
