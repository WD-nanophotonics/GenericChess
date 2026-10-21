# Leaper clocks, composition and learnable signal

Executed 2026-10-21 UTC / 2026-10-22 JST by DEV_AUX. Mainline infrastructure is
fixed at `3ddbf9988e680d473ebe5d90b2a66ec430993df5`: all 238 shared package files
match. Only the existing AUX learner adapters and research code differ. Core,
GameSession, public alpha-beta, terminal/history semantics and ordering are reused.
Numerical evidence: [curated results](data/leaper_clock_composition_20261022.json).
Large traces, graph caches and exact executed-source copies remain ignored locally.

The useful B coefficient depends on composition AND depth in this exposed
diagnostic. After removing the active whole-game clock, D1 makes fewer errors
with low B in ABA but high B in ABC. At D6, low B is again better in ABC.
This is an ordering of search parameters over one fixed distribution, not an
intrinsic A:B ranking, a same-position sign reversal, or population evidence.

## The H6 objection and the exact reference

Claude's Slack comment `1792594110.575129` correctly identifies H6 as a whole-game
rule, not a capture-reset progress counter. Thus H6/D6 terminal PV coverage was
partly built into the benchmark. The old finite-game results remain valid;
their interpretation must not be extended to longer games.

Core requires positive integer `max_ply`. These new capture-removal worlds use
a clock exceeding the number of possible Positions, including side to move.
Repeat-two therefore ends every play before that clock can fire. For one
ordinary actor per side on n squares, the bound is
`2 * (nP2 + 2*nP3 + nP4) + 1`: both Anchors remain, and either ordinary may be
captured. It gives 8,209 / 101,281 / 663,601 for widths 3 / 4 / 5. Coexistence
worlds use the looser `2 * alphabet^9 + 1`, counting empty or owner/type at
every square. Their clocks are also unreachable. This preserves finite play;
it does not add an adjudication to old experiments.

The graph is generated through existing Core legal actions and transitions.
Fresh vertices carry canonical one-occurrence history. A complete graph is
solved by the ordinary winning attractor: a win has a losing child, a loss has
only winning children, and residual vertices draw. Winning distance minimizes
over winning actions; losing distance maximizes over all defenses. Every
decisive rank equation is checked.

This is deliberately a restricted analysis of the constructors in
`leaper_microgames.py`, not a general Position quotient. No drops, promotion,
hands, claims, auxiliary state, progress counters or history-dependent losses
are discarded from arbitrary rules.

| World | Reachable Positions | Edges | Maximum fresh decisive distance | Fresh root result |
|---|---:|---:|---:|---|
| 3x3 MM, all 288 quiet starts | 1,768 | 4,200 | 3 | 80 W / 200 D / 8 L |
| 3x3 A versus King-step B | 2,108 | 5,152 | 8 | 184 L / 104 D, over the same 288 layouts |
| 4x4 MM, corner start | 41,184 | 227,280 | 15 | D |
| 3x3 ABA coexistence | 57,437 | 159,346 | 8 | D |
| 3x3 ABC coexistence | 36,199 | 91,872 | 16 | D |

MM's 288 fresh WDL labels are ALL unchanged from H6. Therefore H6 did not
cause their root WDL distribution. In contrast, A/B-King layout `[6,8,0,2]`
changes from H6 draw to a fresh loss at distance 8. These are different rules;
neither the objection nor the MM negative control applies universally.

The 5x5 MM feasibility run stopped at its declared 120-second cap. It has no
numeric labels or complete state count, and was not extended or refilled.

## Fresh labels do not erase played history

For a fresh winning root, choose a rank-decreasing action on the winner's turn;
every defender action also decreases rank. The resulting strategy cannot repeat
a Position, so its win lifts to actual repeat-two play. Residual draw strategies
avoid the opponent's winning attractor; an actual repetition safely draws.
This justifies fresh-root WDL, not unrestricted lookup during a played game.

For an actual prefix, previous Positions instead become absorbing draw targets.
The current root retains its outgoing moves, but returns to it also draw.
Recomputing the attractor on that remaining graph preserves the actual prefix.
For a first action from a fresh root, blocking return to the parent similarly
scores the child correctly. The learner's search does not consume these labels.

An independent full-history Core unroll checks this construction plus the
remaining H6 distance at ALL 91,712 MM contexts: zero disagreement or missing
labels, 108.48 seconds. In the corresponding longer-clock histories, 68,416
contexts are still ongoing. Of these, 640 fresh losses and 688 fresh wins
become actual draws because of prior history. A separate ongoing four-move
example from layout `[0,7,2,8]` has fresh WIN but actual DRAW. Complete histories
and fingerprints remain bound separately for each rule.

## Composition after removing the active clock

ABA and ABC retain the same initial eight occupied squares and owners. Both
sides replace the extra orthogonal A by horizontal C; A is orthogonal, B is
diagonal, and C has just the two horizontal steps. Royal K keeps King steps.
The initial position and every one of the 186 compared prefixes are legal in
both worlds. All 186 occupancy/owner controls pass.

The prefix distribution is the previously exposed set where BOTH H6 games were
ongoing. It is not every longer-game history and is not held out. Each prefix
is replayed under its own new rule; exact labels use its actual history. A=C=1,
B=r; public q0 queries have fresh TT, zero capture-order prices, 100,000 nodes
and 3 seconds each. The joint 600-second budget includes rebuilding the graphs
for these new labels and retaining compressed local caches.

All 7,440 requested queries finish their target depth; zero missing/UNKNOWN,
511,303 search nodes, 295.28 seconds total. Removing H6 changes the exact label
at 11 ABA and 49 ABC prefixes.

| World | r | D1 errors | D2 errors | D3 errors | D6 errors |
|---|---:|---:|---:|---:|---:|
| ABA | .25 | 11 | 4 | 2 | 0 |
| ABA | .75 | 11 | 4 | 2 | 0 |
| ABA | 1 | 14 | 6 | 2 | 0 |
| ABA | 1.25 | 14 | 6 | 3 | 0 |
| ABA | 3 | 14 | 6 | 4 | 0 |
| ABC | .25 | 26 | 19 | 13 | 3 |
| ABC | .75 | 26 | 20 | 14 | 4 |
| ABC | 1 | 22 | 21 | 16 | 4 |
| ABC | 1.25 | 20 | 18 | 15 | 5 |
| ABC | 3 | 20 | 19 | 15 | 6 |

The D1 aggregate preference changes between worlds, but no individual common
prefix has strictly opposite low-to-high WDL effects in the two worlds.
Of 186 prefixes, 174 have no such effect in either world; eight improve only
in ABC, one worsens only in ABC, two worsen only in ABA, and one worsens in
both. Different contexts drive the aggregate ordering. No statistical
independence, monotone depth law, unique optimum or universal price follows.

One concrete mechanism is prefix index 21:
`(0,1)->(1,2), (0,2)->(1,2), (1,0)->(1,1), (2,1)->(1,0)`.
Player 0 now chooses between taking the unit actor at (1,2) with A, or taking
B at (1,0) with K. D1/r=.25 takes the unit; r=3 takes B.
Both actions draw in ABA. In ABC, taking the unit draws but taking B wins.
After taking B, ABA's defender A can legally capture the attacking A vertically,
`(1,2)->(1,1)`, leading to draw. Horizontal C cannot make that defense.
For ABC, all defenses of a rank-8 winning continuation were replayed through
actual Core: nine nodes, one terminal branch, player 0 checkmate. H6 ends long
before this continuation and conceals the distinction. This is an explicit
geometry/defense mechanism, not an inference from target counts alone.

## Exact cells separate evaluation errors from tie choices

For the original H6 comparison, every material leaf is `a+b*r`. Their pairwise
crossings partition `0<r<8` at `.5, 1, 1.5, 2, 3, 4`; mate constants cannot cross
material scores in this range. Leaf order and hence minimax-optimal action SETS
are fixed inside each open cell. Boundaries are separate. This is an exact
finite-tree statement, not an assumed continuous price law.

All 19,344 public choices at cell representatives/boundaries belong to the
reference heuristic-optimal sets. For ABA/D1, below r=1 there are two contexts
where every heuristic-optimal action is WDL-wrong and six where a heuristic tie
mixes good/bad actions. Above r=1 these become three and eight. ABC/D1 has zero
forced errors and two unsafe ties throughout. Changing price cannot reliably
repair its tie problem. Public tie choices were measured at representatives;
the action-set theorem does not assert a particular implementation's tie choice.

## Deeper requested search and literal targets

The no-active-clock 4x4 MM study selects 64 safe layouts by the pre-existing
SHA ordering, before labels/search. They occupy 64 geometric symmetry classes;
this does not make them independent rule samples. Exact roots are 21 W / 43 D.
Every first-action label explicitly blocks repetition of its parent.

| Requested depth | WDL errors | Target depth finished | Search nodes | Missing literal choices |
|---|---:|---:|---:|---:|
| 1 | 14 | 64/64 | 545 | 0 |
| 2 | 3 | 64/64 | 1,863 | 0 |
| 3 | 2 | 64/64 | 6,387 | 0 |
| 4 | 1 | 64/64 | 14,356 | 0 |
| 6 | 0 | 64/64 | 81,924 | 0 |
| 8 | 0 | 46/64 | 344,925 | 0 |
| 12 | 0 among 59 | 0/64 | 524,288 | 5 UNKNOWN |

All 448 requests ran, within the predeclared 900-second whole budget; actual
time was 199.76 seconds including reference construction. Each query gets
8,192 nodes/3 seconds. D12 returns only completed depths 6 through 11. Five
results have mainline source `completed_root_win`: a winning child from an
interrupted deeper layer replaces the last uniform iteration. This can occur
with `stop_after_root_win=False`. The AUX adapter correctly rejects it as a
TDLeaf target. The committed public interface does not export the displaced
whole-iteration action/PV; no cap refund, rerun or parallel search was used to
fill those five slots. D12's finite error count is bounded by [0,5], not zero
on all 64. A real regression preserves this distinction. Shared search is
unchanged; the useful caller-contract issue is recorded for mainline reuse.

## Learning: updates, actions and WDL are different outcomes

In the longer-clock A/B-King diagnostic, 64 episodes complete at actual rule
terminals, 856 queries / 30,550 nodes. D1 has 18 changing updates, B=.25 to
.322337, but all 186 candidate actions match initial-weight queries at those
same actual prefixes. D6 has 240 candidate queries, only 80 terminal PVs,
yet still zero updates: its 160 nonterminal features have zero trainable
coordinates. There are 12 nonzero TD errors. Thus terminal PVs are not the only
reason a deeper material learner can have no gradient. All 64 histories and
426 TD terms were independently checked with zero arithmetic discrepancy.

For a second, symmetric ABC mechanism check, the existing learner starts uniform
and plays fixed uniform D2, alternating colors at ONE fresh root. The runner
has no oracle interface. Budget: 32 episodes, 120 seconds/2M nodes, 64 plies and
524,288 nodes/10 seconds per game. Actual: 32 draws, two distinct trajectories,
469 queries, 5,566 nodes, 3.34 seconds. There are 31 changing updates and 78
nonterminal candidate PVs with trainable features. Final B=.9996082781,
C=.9999971296. These are not measured intrinsic prices.

The new AUX receipt retains literal public PV choices, including declarations;
historical reference receipts remain explicitly empty. All 469 saved PVs replay,
all exact observer labels at their leaves are draw, and both players' selected
actions are exact-WDL optimal along the experienced paths. Independent forward
TD arithmetic checks all 227 terms with zero discrepancy. At identical actual
prefixes, 210 new initial-weight queries plus 17 identical-weight cases find
15 action changes, ALL equal WDL. Updates and changed moves therefore do not
establish improved play. The next learning question needs rule-independent
opening variation, not more copies of these two trajectories.

## Advice, retained failures and next action

The old task2625 candidate-first 49:16 sign calculation is numerically
`p=0.0000508477` under hypothetical independent fair signs. It is NOT a clean
weight-effect estimate: first divergence is selected after treatment, and the
endpoint seed changes candidate tie ordering too, as well as later foe moves.
Its 213 candidate-first pairs include 132 ties and 16 UNKNOWNs. Foe-first
differences are 39 positive / 18 negative / 109 tied / 24 UNKNOWN when draw flips
are included. The old bounds remain descriptive; no old game was rerun.

The next composition check swaps the initial A/B squares on both sides in ONE
declared matched layout, keeping the extra actor squares fixed. Both saved starts
already compile, with 4/3 legal root actions, and are not D4 copies of the old
boards. Their exact longer-game values have not been computed. It tests whether
the D1 preference contrast survives a layout intervention. A backup draws legal
opening prefixes from a fixed RNG without exact-label selection, then measures
whether experiential learning encounters any actual regret. Neither is a large
grid, old panel resumption or an oracle-labelled training curriculum.

Old stopped jobs, missing slots, raw trajectories/models, 5x5 timeout and five
nonliteral D12 results remain intact. No other role files, new workers, schedules
or project visibility were changed. The existing 90-minute heartbeat remains.
127 relevant regressions pass, including real Core/history, material-cell,
literal-PV, learner arithmetic and interrupted-root-result checks.

Reproduction uses fresh output directories:

```powershell
.venv\Scripts\python.exe -m scripts.leaper_retrograde artifacts/new-MM
.venv\Scripts\python.exe -c "from scripts.leaper_microgames import composition_parameter_cells; composition_parameter_cells('artifacts/new-cells')"
.venv\Scripts\python.exe -c "from scripts.leaper_retrograde import composition_without_clock; composition_without_clock('artifacts/new-composition')"
.venv\Scripts\python.exe -c "from scripts.leaper_retrograde import fresh_depth_study; fresh_depth_study('artifacts/new-depth')"
.venv\Scripts\python.exe -c "from scripts.leaper_retrograde import experiential_probe; experiential_probe('artifacts/new-experience')"
```

These are reproducibility entries, not authorization to refill closed runs.
