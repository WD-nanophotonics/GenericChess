# Experiential C learning, prior controls and search depth

The existing TDLeaf learner learns useful horizontal-C behavior without oracle
targets. Its benefit depends on the initial B, opponent, state distribution and
search depth. Three foe streams produce different weights but identical measured
policies within each initialization group. This is evidence of finite policy
stability, not convergence to an intrinsic C price. Deeper search removes much
of the parameter advantage and exposes a genuine completed-depth regression.

Evidence: [compact configurations, tables and selected executable witnesses](data/leaper_C_learning_depth_20261022.json).
This exposed, selected Leaper study does not establish independent-rule or
held-out generalization. Full journals and one-off drivers remain ignored local
artifacts; the compact file does not publish every raw trajectory.

## Fixed learner and experience

Execution uses runtime source `734d606f8f6594820d457803bf8f5dbe5e0666f4`
and committed sandbox infrastructure
`a552355e32a39fcff7d720d1181aebb904b79b79`. The same Core, GameSession,
terminal/history authority and public iterative q0 search are reused. No engine
default or second rules executor is introduced.
Closing fetch is `69a3c84ab0be9875611e751e78d3225f0fa8973c`; its new changes
are PRIMARY research records only. All238 shared package files still match
that committed infrastructure, and there are no new shared test changes.

The already solved 3x3 ABC-H world has orthogonal A, King-like B, horizontal C
and King-like Anchors. Captures remove ordinary pieces; actual mate, stalemate
and repeat-two rules govern outcomes. Its very large finite max-ply bound is
inactive. The rollout's separate 64-move allowance can still censor a game.

The 128 previously frozen uniformly legal opening walks use seed 2026102221,
target lengths cycling 1–6. Their byte hash is
`b07b23b72f2ce83fb3c8ab57e288f3608ca64bdf1cab1a007050d162207572c7`.
All terminals and duplicate histories remain: 11 terminal and 117 ongoing
prefixes. Each arm plays 512 episodes: two trials of every prefix in both colors,
in the original fixed order. The foe is uniformly random among actual legal
actions, with seed 2026102222 plus episode index, identically coupled across arms.
After different actions, this does not imply identical random choices.

The initial board weights are `(A,B,C)=(1,1,1)` or
`(1,2.4171096107122936,1)`. A remains fixed; scale=10, eta=.05 and lambda=.95.
Weights freeze within each episode and update once afterwards. Search-to-search
targets train; only an actual rule terminal supplies the final W/L/D target.
UNKNOWN withholds that final target. Neither the training runner nor its API
receives oracle labels.

Implementation qualification: the transferred initialization also sets the
unused hand-B channel to 2.417, rather than leaving it at one. Hands and all
their features/updates are identically zero in this remove/no-drop world. The
literal six-channel arrays are retained; no hand-value learning is claimed.

| Initialization | Final B | Final C | Actual W / D / L / UNKNOWN |
|---|---:|---:|---:|
| Uniform | 1.394998 | .574019 | 214 / 234 / 58 / 6 |
| Transferred B | 2.770482 | .567647 | 225 / 224 / 57 / 6 |

Both arms complete all 512 slots within their unchanged 120-second / 2M-node
allowance, taking 25.47/24.67 seconds and 33,322/32,529 nodes. Training outcomes
are adaptive experience, not frozen-model strength estimates. The 12 censored
games remain UNKNOWN.

## Frozen choices and actual random-foe games

All final models freeze before evaluation. The same 128 histories, both colors
and a declared RNG stream give 256 games/model. The table concerns H; all 117
ongoing root queries complete D2. Terminal prefixes remain in the game count.

| Frozen model | Opening errors / 117 | W / D / L / UNKNOWN |
|---|---:|---:|
| Uniform initial | 12 | 92 / 131 / 32 / 1 |
| Uniform learned | 3 | 104 / 120 / 31 / 1 |
| Learned uniform B, reset C=1 | 7 | 99 / 126 / 30 / 1 |
| Transferred initial | 6 | 107 / 118 / 30 / 1 |
| Transferred learned | 2 | 116 / 109 / 30 / 1 |
| Learned transferred B, reset C=1 | 6 | 107 / 118 / 30 / 1 |
| Zero-training mobility prior | 2 | 109 / 116 / 30 / 1 |

The mobility prior uses empty-board mean geometric degree, normalized to A:
orthogonal 24/9, King 40/9 and horizontal 12/9 give B=5/3,C=1/2. This is a
rule-derived baseline, not an oracle-selected constant.

Paired score gains over each arm's own initial model have censoring bounds
`[11/512,15/512]` and `[7/512,11/512]`. The transferred learned model exceeds
the mobility prior by `[5/512,9/512]`, whereas the uniform learned model is
below it by `[-1/64,-1/128]`. These are finite worst-case bounds for unknown
endpoints in [0,1], not confidence intervals or independent-game inference.
Resetting C isolates its contribution to the frozen policy, not the causal
effect of retraining with C fixed.

The original evaluation base seed 2026102223 has numerical seed overlap with
the training range, and all opening histories are exposed. It is not independent
validation. The later stability evaluation below uses a disjoint RNG range.

The horizontal learner is also frozen on the existing vertical-C world, with
no V training. Opening errors change 21→17 and 11→11; resetting C gives 17/11.
Yet full-game transferred-model gains over its initial model remain bounded
by `[1/512,7/512]`. Opening-choice equality does not establish equality on later
experienced states. V has 12 censored evaluation games, retained separately.
The H and V evaluation batches each record all 1,800 planned games, including
eight one-root deterministic controls; their conclusions are not based on those
eight repeated-root controls alone.

## What C actually fixes

At H opening34, the actual five-ply history reaches:

```text
C1  . K1
 . A1  .
K0 C0  .       player1 to move
```

All Bs have disappeared. Literal Core two-ply reply trees give the player-0
scores `[-1,0,-C,-1,-1,-1,-1]` for C>=0. The root minimizes, so its critic is
`min(-1,-C)`, constant -1 throughout 0<=C<=1. C=1 lets A1 b1-b0, a DRAW action,
tie with WIN actions. Lower C removes that action from the best-score set;
actual search selects C1 a2-b2, a WIN. A six-node all-defense WIN certificate
is stored and independently replayed.

Another DRAW action still scores -1 for every C. Thus lowering C does not make
every D2 maximizing action correct, nor identify a unique C. Four weighted
opening entries show this rescue, but they contain only two distinct histories
and one board. At the selected C=1 PV, the retained leaf has a C gradient; after
the choice changes, the selected leaf has zero C gradient while the critic
remains -1. This explains useful movement across a policy boundary without
equating the retained leaf semi-gradient with the derivative of the minimax
envelope.

The new Chat suggestion to cross-tabulate gradient support and strategic choice
was applied to existing data, without selecting training openings by labels:

| World | Nonzero C gradient | Also different-WDL actions available | C=0 improves chosen WDL |
|---|---:|---:|---:|
| H | 35 | 23 | 4 |
| V | 46 | 29 | 0 |

All four H rescues have gradient support; 12 H and 17 V gradient-bearing
prefixes have no WDL distinction among their legal actions. Nonzero gradients
alone do not measure strategic information. All rows retain duplicate weight.

## Credit, winners and numerical non-identifiability

All original 1,024 updates reconstruct exactly with the saved episode-frozen
gradients. The forward origin-credit sum agrees with the backward eligibility
sum. Total C changes split as follows:

| Initialization | Interior TD terms | Final-outcome term | Total |
|---|---:|---:|---:|
| Uniform | -.40680423 | -.01917657 | -.42598080 |
| Transferred B | -.41341110 | -.01894223 | -.43235333 |

Interior transitions include transitions into search PVs ending in an actual
mate. A small final-outcome term does not imply that terminal information is
unimportant. The censored episodes have no invented final error.

Selected post-hoc actual-history cases make the distinction concrete. Uniform
episode123 wins for player1 but has learner WDL-gap sum2 and foe sum2. Its
largest C decrease, -.033261, comes from eight accumulated positive C gradients
followed by a search value reaching the player-0 loss target. Uniform episode268
starts as a learner LOSS and ends WIN: learner gap0, foe gap2. It raises C by
.049337. Winning does not imply an optimal trajectory or a fixed update sign.
For every selected complete episode, `final learner payoff - initial exact
learner WDL = foe gaps - learner gaps`. These selected examples are not estimates
of the frequency of such mechanisms.

Two further foe streams were fixed before their runs: 2026103232 and 2026104242.
They change only opponent randomness, not the ordered openings, learner or
512-episode allowance. All four new arms complete; 28 additional training
UNKNOWNs remain. Every update reconstructs within 2.23e-16.

| Foe seed | Uniform final B,C | Transferred final B,C |
|---|---|---|
| 2026102222 | 1.394998, .574019 | 2.770482, .567647 |
| 2026103232 | 1.377101, .497415 | 2.845346, .456887 |
| 2026104242 | 1.269636, .541261 | 2.783481, .487341 |

Evaluation uses base seed2026110000, disjoint from all training ranges. All
2,304 games complete their slots. Within each initialization group, all three
learned models have identical 117 opening choices AND identical 256 complete
game records. Uniform-trained models give 110W/115D/30L/1UNKNOWN; transferred
models 119W/107D/30L/0UNKNOWN. The mobility prior gives
116W/109D/30L/1UNKNOWN. Numerical endpoints differ while the observed policy
stays unchanged. This finite equivalence does not cover unvisited positions,
other opponents, a changed opening order or other rules, and is not convergence.

## Depth changes both adequacy and tie behavior

The already frozen 749 common fresh-root boards are reused, with their original
exact action labels. They are constructed reachable boards with fresh histories,
not 749 independent rules or original-root trajectories. All 41,944 public
queries complete D2/D4/D6/D8, using 5,827,278 nodes in 1,113.30 seconds under
the declared 1,200-second / 6M-node cap. There are zero fallback or missing queries.

| World / model | D2 errors | D4 | D6 | D8 |
|---|---:|---:|---:|---:|
| H uniform initial | 59 | 12 | 9 | 4 |
| H uniform learned | 35 | 9 | 6 | 3 |
| H transferred initial | 38 | 8 | 5 | 2 |
| H transferred learned | 28 | 8 | 5 | 2 |
| H mobility | 29 | 9 | 6 | 3 |
| V uniform initial | 69 | 20 | 12 | 6 |
| V uniform learned | 36 | 11 | 9 | 5 |
| V transferred initial | 44 | 12 | 8 | 4 |
| V transferred learned | 29 | 10 | 8 | 4 |
| V mobility | 31 | 11 | 9 | 5 |

At H D4, resetting the uniform learned C to1 lowers errors9→8, despite raising
D2 errors35→45. At panel720, both C settings have the identical Core D4 root
score vector: `[-1-B,-1,-1000000,-1]`. The two -1 actions have LOSS and DRAW
labels. Actual iterative search picks LOSS after lowering C and DRAW at C=1;
D2 and D6 pick DRAW in both cases. A 32-node opponent WIN certificate after the
bad action confirms the consequence.

The selected 24-query ablation isolates iteration/TT-conditioned tie ordering:
with ordering retained and TT disabled, both D4 choices draw; with ordering
disabled both lose. This is not evidence that disabling TT or ordering improves
the engine. Root values are correct; the finite-depth material tie is ambiguous.
This completed-depth nonmonotonic case has no timeout/fallback confound.

An independent existing q0 AlphaBeta reference using actual GameSession/Core,
with runtime acceleration disabled, checks 146 root values and forced deployed
action values across four depths, two worlds and three models. Six salted-hash
roots plus two explicitly post-hoc D8 errors are checked. All agree in normalized
score space; mate-distance tie choices are not asserted equal. This is a bounded
semantic control, not a claim that all 41,944 trees were independently rebuilt.

## Stronger foes and the cheap-prior objection

The new direct C experiment makes both players search at the same declared
depth. It compares each learned model with its own initial model, plus transferred
learning versus mobility, across both colors and the existing H/V openings.
Its original 20-minute wall cap stops it at 2,296 recorded games: **3,848 planned
slots remain missing**, with 43 recorded UNKNOWNs and no search-depth fallback.
No missing slot is filled or turned into a draw. All 47 fully completed ordered
openings, plus 40 tail games, remain in the data. The common-cohort tables and
all-record tables are separate. H's deeper direct results are near balance;
V censoring prevents a general adversarial-strength conclusion. Positive RNG
gains must not be promoted to broad strength from this partial experiment.

Claude's mobility objection was also checked in the OLD KAB King-B benchmark.
On its same 1,824 quiet layouts excluded from the original training starts,
D2 errors are 381 for uniform, 189 for mobility B=5/3, and 170 for the old
TD B=2.417. Of the 211 fewer errors versus uniform, the cheap prior already
accounts for192; TD corrects another19, with no reverse WDL change on this panel.
These exposed layouts are not a new untouched holdout.

A separately bounded actual direct-play control completes all 7,296 games:

| Requested depth for both players | Old TD W / D / L / UNKNOWN versus mobility | TD score minus 1/2 |
|---|---:|---|
| D2 | 1163 / 1360 / 1125 / 0 | 19/3648 |
| D4 | 1365 / 1007 / 1271 / 5 | [89/7296,99/7296] |

Both colors are used once per layout; all queries complete the requested depth.
This establishes a small finite direct-play advantage over this prior, not just
an advantage over uniform. It does not establish an intrinsic B, independent
world samples, an Elo estimate or universal superiority of TD.

The old ideal uniform-tie census supplies a different decomposition on ALL
1,952 quiet side0 KAB roots:

| Depth | Uniform expected errors | Best global B | Per-root oracle B |
|---|---:|---:|---:|
| D1 | 1636/3 | 1060/3 | 904/3 |
| D2 | 1202/3 | 160 | 156 |
| D4 | 3574/15 | 38 | 112/3 |

These use positive B in the declared (0,4] leaf-order domain, A fixed and ideal
uniform ties. The uniform-to-global gap, global-to-per-root gap and remaining
error are distinct. The final column is not a lower bound for every conceivable
material representation or deterministic tie policy. It must not be subtracted
from the actual 1,824-root public errors as if those were the same experiment.

## Second conditional-contribution reversal

The previously unexpanded panel593 case is now checked through six shortest
legal prefixes from the unchanged original rules. Fresh and actual-history
owner1 values agree:

| World | Original | Remove original A1 a1 | Remove B1 c1 |
|---|---|---|---|
| ABA | WIN | LOSS | DRAW |
| ABC-H | DRAW | DRAW | LOSS |

Prefix lengths are 4/8/10 and 4/8/12. Three WIN certificates have 5/2/4 nodes.
The second A at a2 protects A1 a1 vertically; horizontal C does not. When A1
is removed, A0 at c0 supports B0's immediate mating capture on c1, whereas
horizontal C0 does not supply that vertical support. The geometry changes a
mating coordination, not an additive price. Deletion remains a constructed-state
intervention; separate realizability prefixes are not literal deletion actions
or matched causal gameplay. DRAW labels still depend on the complete component,
not a portable finite WIN proof.

## Verification, costs and next decision

All original training/H/V evaluation records replay: 4,624 games, 21,478 search
receipts and 39,868 PV edges. Newly closed records replay separately, checking
every recorded move, query action and RNG choice; PV/leaf replay there is the
fixed episode-mod64 sample, explicitly not every PV. The compact data stores
the actual counters and local-only journal hashes. All 124 existing relevant
learning/runtime, Leaper and terminal-aware game-quality tests pass. Private
JUnit machine metadata and raw Slack account metadata are excluded.

The two additional training seeds take111.35 seconds total under four independent
120-second / 2M-node arm caps. The direct C cap is retained; the complete KAB
direct control takes598.46 seconds under900. Stop flags were polled throughout.
Some own bounded computations overlap; no performance
acceleration or isolated throughput is inferred from these timings.

Preserved repairs: an evaluation-driver syntax error ran no computation; the
first replay confused episode-relative callback ply with absolute ply and
failed before checking a query. Adding the recorded prefix length repairs it,
charging .076674 seconds to the same180-second allowance. The first-fork
observer stops at its32-unique-history cap during the fifth comparison; its
missing mobility fork labels are not filled. Keep the prior80 deletion UNKNOWNs,
88 unlabelled keyed-geometry queries,65 old UNKNOWN games and394 unprocessed
historical oracle queries unchanged.

The existing `experiential_probe` reproduces each arm with episodes=512,
depth=2, lineup=('A','B','C'), c_axis='horizontal', b_geometry=KING,
opening_count=128, opening_seed=2026102221, the declared foe seed and the literal
initial array. Oracle observers run only after model freezing. The earlier
composition report describes rebuilding the exact components and frozen749
panel. Compact selected rules, histories, reply trees and WIN strategies permit
independent inspection without treating unpublished full journals as remote data.

Next distinguish useful acquisition from retention: does changing the ORDER of
the same label-blind opening multiset, while keeping the fixed foe stream and
all budgets, move the final model into a different measured policy region?
That changes a specific remaining premise; another unchanged seed rerun or
completion of the capped direct slots does not. Compare actual frozen actions
and terminal play with the existing mobility prior; numerical C agreement alone
is not the success condition. No new representation, broad hyperparameter grid,
oracle-filtered training or product default is selected.

The next order protocol is frozen locally and **not launched**: reverse the128
opening groups within each trial, retain color0 then1, and bind foe randomness
to canonical slot `256*trial+2*opening_index+color`, not the execution index.
Otherwise changing order also changes the stream assigned to each opening.
On117 unchanged ongoing openings, a direct no-search first-foe-choice control
changes55 actions under naive execution-index reseeding; the11 terminal
openings remain retained. This measures the stream-assignment confound, not
an actual training-order effect.
Use existing `play_episode` with that explicit RNG policy; no learner rewrite
is needed. The two arms retain120seconds/2Mnodes each, followed by600seconds
evaluation and180seconds replay. Check source compatibility before an order-only
interpretation. Merely permuting the old saved update vectors would preserve
their sum and would not test the state-dependent learning process.
