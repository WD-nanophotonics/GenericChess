# Leaper experience, value fitting and decision equivalence

The broader experience controls expose a specific limitation: a useful action
boundary can be rare, and visiting it need not give the selected PV a material
gradient. Much of the observed downward B update instead originates in states
from which no strategy can reach a decisive terminal. Fitting those states can
conflict with good shallow decisions elsewhere. This is a conditional
representation and sampling result, not an intrinsic price or a TD convergence
claim.

Two new 776-episode training arms finish with different B values but identical
public decisions on all 388 tested starts. Both also match an already frozen,
untrained B=0.75 control. Their one repaired WDL decision relative to B=1 does
not establish a benefit of training over that cheap control. No evaluator,
weights or game defaults are selected.

Numerical evidence and selected executable inputs are in
[leaper_experience_value_20261022.json](data/leaper_experience_value_20261022.json).
Full journals, graphs and one-off drivers remain local. The compact evidence
does not make every raw trajectory remotely available or claim independent
external execution. All comparisons below use exposed data from a small
component; none is a held-out or cross-rule strength test.

## Rules, infrastructure and preservation

The committed sandbox baseline is
`60e1b23c87002f81f19994bd68f9ffa20437a57b`. Its completed post-proof
cancellation/deadline repair, public search tests and semantic cost-probe
changes are reused. All 238 shared package files match after line-ending
normalization. The two existing AUX learner modules remain the only package
additions. Four test exceptions retain the documented role-specific/historical
boundaries; PRIMARY and DeepSeek state are untouched.

Rules, initialization, actions, terminal/history semantics and public q0 search
use GameSession/Core and the committed mainline. The only new research helper
option is episode-frozen adaptive selfplay: both sides use the current model
at the same depth, then the existing TD update runs once after the episode.
The default fixed uniform opponent is preserved. Tests exercise both players
with a nonuniform model at D1 and D2 and reject combining selfplay with a
random foe.

The preceding segment was ended. This segment has its own UUID; old task2620,
task2625, interrupted work, models, caps, missing slots and UNKNOWN outcomes
remain closed and unchanged. No extra Agent, worker, Goal or timer is created.
The existing 90-minute recurrence is not modified. New Slack advice is adopted
with the distinctions below; the historical uncertain report is not resent.

## Local signed-price repair and its boundary

The already admitted ABC root 318 has four actions with exact root-player
labels `[DRAW,DRAW,LOSS,DRAW]` in the retained inventory order. At C=0, D4:

| B | Scores in inventory order | Selected set |
| --- | --- | --- |
| +1/4 | -1, -1, -5/4, -1 | Three DRAW actions |
| -1/4 | -5/4, -5/4, -1, -5/4 | The LOSS action |

Ten actual public root/forced-child searches complete in 555 nodes. The
negative-B PV preserves equal B counts at its leaf; competing drawing branches
can leave an extra own B, which negative B penalizes. The loss is not inferred
from a static score: the opponent's rank-11 strategy after that action is
replayed through actual Core against every defense, with 22 visited nodes.
The heuristic PV and the opponent's winning strategy need not be the same path.

This is not an unrestricted material impossibility. Adding the new root to the
old 52 D4 trees, a complete rational leaf-order arrangement on [-4,4]^2 still
has zero-error points. At fixed B=-1/4 the exact joint safe slice is
**1/4 < C < 1**, including its internal equality boundaries. C=1/4 and C=1
are unsafe. B=-1/4,C=1/2 passes all 53 actual public D4 queries.

With C fixed at zero, H137 plus ABC318 have a minimum combined uniform-tie
error of 1/2 over B in [-4,4]. Allowing C to change repairs the pair. A separate
same-inventory H/V geometry control at root 137 has a weaker V restriction:
within this box every H-safe cell is V-safe, while B=C=0 is V-safe but H has
error 1/2. This is one matched geometry case, not a universal ordering reversal.

The initial 2D observer accidentally paired labels with a different action
enumeration. That result is invalid and retained privately. Binding labels to
literal actions repairs it; the two computations total 74.778 seconds within
the original 120-second allowance. Public controls use action-bound labels.
No negative-price default or learned conditional C value follows from these
oracle-selected, post-hoc repairs.

## Prospective fixed-policy experience controls

Reuse the earlier 49 valid AB starts: one K, A and B per owner, capture removal,
repeat-two and an inactive rule clock. Eight trials and both designated learner
colors give 784 games per protocol. The critic is fixed at A=1,B=1/2, D2.
Foe randomness is coupled by slot. Equal requested games do not imply equal
query counts, costs or independent observations.

| Protocol | Candidate queries | Search nodes, both sides | W/D/L/UNKNOWN from designated color |
| --- | ---: | ---: | --- |
| D2 versus legal RNG | 7,398 | 90,723 | 96/662/10/16 |
| Frozen D2 on both sides | 7,720 | 173,248 | 56/656/56/16 |
| D2 versus RNG, truncate after 8 noncaptures | 3,839 | 49,324 | 96/336/10/342 |

All 2,352 games finish their declared production, with zero missing games,
in 182.783 seconds and 313,295 search nodes. The third protocol's 342
truncations remain UNKNOWN. Their prefixes match the corresponding RNG paths;
they are not resignations, adjudications or actual draws. The repeated frozen
selfplay trials contain just 49 distinct complete records, not eight
independent replications per start.

The complete-history observer reaches its original 1,200-second cap after
18,563 of 18,957 candidate queries. Its 394 unprocessed queries remain
unprocessed; no refill is launched. It completes 766 games per protocol, plus
a partial next-game query prefix. Observed counts are:

| Protocol | Observed / requested queries | Draw-only closure visits | Changed B=.25/.75 argmax | Different uniform-tie WDL expectation |
| --- | ---: | ---: | ---: | ---: |
| RNG | 7,251 / 7,398 | 5,809 | 107 | 0 |
| Frozen selfplay | 7,547 / 7,720 | 6,165 | 79 | 0 |
| Capture reset | 3,765 / 3,839 | 2,327 | 107 | 0 |

These are prefix observations. In particular, zero observed strategic contrasts
does not fill the missing 147/173/74 queries or establish a zero population rate.
The observer needlessly recalculated attractors inside the known draw-only
closure. Later observers avoid that redundant calculation; this cap and its
missing coverage are preserved rather than repaired by a budget extension.

A fourth, separately frozen intervention changes candidate behavior too:
both sides play uniformly legal moves, while a D2 critic is queried but its
recommendation is not played. It is a later exploratory comparison, not a
predeclared four-arm trial or off-policy TD training. Its 784 games are all
actual terminals: 19W/735D/30L, zero missing/UNKNOWN, 47,405 critic nodes.

Its complete observer finds 133 argmax boundaries and **one** different
uniform-tie WDL expectation among 3,955 queries. At that full history, the low
price has an unsafe tie and the high price is tie-safe. Actual public low/high
queries both choose exact-WDL DRAW actions, however. The one exposure does not demonstrate an
executed price-dependent WDL gain. A six-node all-defense certificate verifies
the losing alternative in that actual history.

## Why the information is rare

The complete existing component has 4,880 ongoing fresh positions with exactly
one K/A/B per side. There are 400 B=.25/.75 D2 argmax boundaries, but only
16 change uniform-tie WDL expectation. All 16 change it from -1/2 to zero.
They reduce to eight physical boards after normalizing the player to move.
All are quiet and valid actual initial positions; they were not excluded by
initialization semantics.

Of 2,480 side-0 inventory candidates, actual public admission accepts 1,888
and rejects 592 with INITIAL_ANCHOR_ATTACKED. Eight accepted starts are
strategic boundary cases: ideal uniform initial exposure is only **1/236**.
The old 49-start pool contains none. Under an ideal uniform sample of 49 valid
starts without replacement, missing all eight has probability about 0.810.
That combinatorial calculation is not a confidence statement about a fixed hash
seed or about subsequent on-policy visits.

A new fixed seed orders 512 candidates before admission and label lookup.
There is no replacement: 388 are admitted, 124 rejected, and three of the
admitted starts are strategic cases. Public D2 queries at B=.25,.5,.75,1
complete all 1,552 slots with zero missing/UNKNOWN. Actual suboptimal counts
are 5,4,4,5 respectively. Oracle labels diagnose these queries after execution;
they never choose or train the starts.

All 4,880 intact roots have material vector (0,0). Static root material therefore
cannot identify their differing WDL, although searches reach post-capture
leaves with useful differences. The exact bounded B curves show another
conditional distinction:

| Depth | A best B cell in [-4,4] | Minimum total uniform-tie error / 4,880 |
| --- | --- | ---: |
| D1 | (0,1) | 168 |
| D2 | (1/2,1) | 152/3 |
| D4 | (1,2) | 8 |

The complete leaf-order partition includes point boundaries. These are ideal
fixed-depth action-set errors, not deployed game win rates or independent
samples. The useful cell changes with depth; the numbers are not intrinsic
piece values.

## Learning, equivalence and actual update origins

The existing learner now makes one pass over both colors of the 388 starts,
from uniform initialization. Each arm has its own frozen 120-second/2M-node
cap. Neither extends an old run. Both complete all 776 episodes:

| Opponent | Final B | W/D/L/UNKNOWN | Seconds / search nodes |
| --- | ---: | --- | --- |
| Legal RNG | 0.861857003 | 125/639/4/8 | 59.677 / 79,217 |
| Current model, episode-frozen D2 selfplay | 0.979726220 | 60/654/60/2 | 77.843 / 120,388 |

The totals describe different training processes and opponents, not a frozen
strength comparison. A complete observer covers 11,760 learner queries in
461.105 seconds. RNG exposes four distinct strategic histories; adaptive
selfplay exposes three. Their actual choices at those histories are optimal.

The selfplay arm's three strategic queries have selected PV material vector
(0,0), hence exactly zero B gradient, including one with nonzero lambda error.
RNG's four such queries have two zero gradients and two positive gradient-origin
credits, totalling +0.0003327955. More decision-boundary exposure does not imply
more gradient signal. Zero gradient is not itself a mistake here: the actual
actions were already safe.

For a frozen episode, rewrite the implemented update as

`delta B = eta * sum_k g_k * sum_(i>=k) lambda^(i-k) TD_error_i`.

Reconstructing every update with the original predictions, gradients and actual
terminal reward gives maximum error 1.11e-16. The allocation by gradient origin
is:

| Arm | Draw-only-state origins | Origins outside that closure | Net B update |
| --- | ---: | ---: | ---: |
| RNG | -0.197027758 | +0.058884761 | -0.138142997 |
| Adaptive selfplay | -0.138782181 | +0.118508401 | -0.020273780 |

This is frozen-path arithmetic, not a causal ablation: later errors credit
earlier gradients, and changing updates would change later play. It shows that
the downward totals do not originate primarily in the rare tested WDL
boundaries. No oracle filter is introduced into training.

An explicitly **oracle-supervised diagnostic control** fits value zero to the
saved nonterminal PV features whose query states are in the verified draw-only
closure. It uses no new games and supplies no labels to experiential learning.
For `L(B)=mean(tanh((a+bB)/10)^2/2)`, strict convexity on [-4,4] and exact
derivative sign bounds prove a unique optimum in **(0,1/2)** for both arms'
feature histograms. Numerical optima are about 0.04852 and 0.32442. Yet that
cell has D2 uniform-tie error 176/3 on the intact fresh benchmark, eight more
than the (1/2,1) cell. Correctly fitting forced-draw material predictions can
therefore conflict with good decisions elsewhere. This is not a TD fixed-point
or convergence result; both actual final models stay above 1/2.

The two learned B values themselves cannot identify a unique useful price.
With capture removal and at most one A/B per owner, every nonterminal leaf is
`a+bB`, a,b in {-1,0,1}. The only crossings in [-4,4] are
-2,-1,-1/2,0,1/2,1,2. All nine forms have the same weak order throughout
(1/2,1). Draw zero and material-dominating terminal constants preserve that
order; any complete finite minimax expression preserves its root argmax sets.
This statement concerns ideal action sets, not numerical predictions, training
gradients or timed-search behavior, and excludes C, drops, promotion and new
actors.

Actual public tests corroborate the finite scope: both final models have
identical actions, PVs and node counts at all 388 starts. Each changes 78
actions relative to B=1; only one changes exact WDL, DRAW to WIN at root 44282.
An actual all-defense WIN certificate verifies the new move. But the already
frozen, untrained B=.75 queries match both learned models on every action, PV
and node count. No training advantage over that control is demonstrated.

## Wins, losses, checks and next question

Selected saved-order examples retain complete records. In frozen selfplay
episode 187, the designated candidate throws a WIN to DRAW at ply 2; the foe
then throws DRAW to LOSS at ply 5, and the candidate wins. In RNG episode 2175,
the foe first throws WIN to DRAW, then the candidate throws DRAW to LOSS and
actually loses. The observed original RNG wins contain no candidate-error
rescue in the audited prefix; do not invent one to fit a narrative. The later
both-random arm has two such wins. These examples are post-hoc mechanisms,
not independent validation.

All 4,688 new game records, 47,710 public PVs, 25,376 RNG choices and 1,552 TD
updates replay through actual GameSession/Core. All 384 original UNKNOWN
outcomes survive. This semantic replay does not fill the separate 394 missing
WDL-observer queries. Initial field-name mistakes in local one-off observers
are retained; no failed output is promoted as a result.

The next useful question is whether a small, label-blind inventory-conditioned
representation can separate forced-draw value calibration from shallow
decision quality. First use the saved feature histograms and exact benchmark
to state a falsifiable comparison and its cost. A first feasibility check is
already begun: six of sixteen inventory classes mix ongoing draw-only and
non-draw-only positions in the existing component. Inventory alone is not an
exact dead-state detector. Component boundaries also matter: a quiet, actually
admitted A+B-versus-bare-K fresh start outside the old component has a legal
mate in one. Its standalone RuleSet/record are retained; it is not appended to
a closed training pool or used to revise old labels. Do not automatically add a
positional patch, train with oracle dead-state filtering, extend the closed
776-episode arms or expand to D/larger boards. A cheaper independent
continuation is the retained matched C-geometry feasibility comparison.

Validation: 154 relevant learner, Leaper, adapter and semantic-cost tests pass;
30 mainline search tests also pass. The latter use the literal mate fixture
extracted from its test module to avoid importing an unrelated optional Qt UI;
no product search module is mocked. Ordinary collection first failed for the
absent optional Qt dependency and a non-writable default temporary directory;
headless fixture loading and an in-checkout temporary directory resolved these
environment issues. Optional-native assertions retain the mainline tests'
conditional behavior; this is not a claim of GUI or universal native coverage.
The outgoing selected proofs rebuild two full D4 Core trees and replay four
actual all-defense WIN certificates. Rational checks independently verify the
C=0 pair bound and both supervised-fit optimum brackets.
