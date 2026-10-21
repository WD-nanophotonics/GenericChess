# Leaper foundations: exact choices, conditional contribution and learning

The direct user instruction in [LEAPER_DIRECTION.md](LEAPER_DIRECTION.md) now
replaces expansion of the old Chess/TDLeaf strength, lambda and opponent panels.
This first investigation has actual exact-game, public-search, learning-process
and saved-trajectory results. No product weights or defaults were selected.

The executed rules/search baseline is committed sandbox
`6ea35571272708f7e220fa3868f2ca1a4d0cf7ca`; the inherited learner library is
at `2006f9830fa6cdf642b094ae179abca694931f7b`. All transitions below use its
Core or GameSession, and decisions use its public AlphaBetaPlayer through the
existing receipt adapter. The new script only constructs experiments and
unrolls a finite game using those authoritative transitions. It contains no
second move generator, terminal authority or evolving alpha-beta engine.
Closing fetch3ddbf9988e680d473ebe5d90b2a66ec430993df5 changes no shared package
file. Its existing capture-only-qsearch CLI forwarding is synced exactly, with
no selective q option enabled in these q0 experiments.

[Curated numerical evidence](data/leaper_foundation_20261021.json) contains
the tables, legal counterexample rule recipes/records, exact reference checks, costs,
recording corrections and old-asset hashes. Large journals remain ignored.
The maintained script includes later width/C and explicit logging extensions.
Captured pre-extension source snapshots/hashes remain local where recorded;
reproduction at the published revision is a new measurement, not an assertion
that every earlier driver or timing experiment was published byte-for-byte.

## Old task closed without a refill

The previous three-condition opponent-control producer received the existing
cooperative stop signal, solely for the requested research redirection. It
exited **0 / STOPPED_USER**, after **999.223289 s / 2,079,852 nodes**. Its
132 histories, 5,802 queries and 116 TD calculations were checked; independent
forward-update error is at most 8.88e-16. Seed27200 finished its16 direct slots:
3W/11L/2UNKNOWN, payoff completion bound [-5/8,-3/8]. The other32 planned slots
remain missing; interrupted training and frozen weights/configurations survive.
There is no three-seed conclusion. Prepared depth and fresh-natural-rule plans
are deferred, not a recovery queue. No old sample or budget was restarted.

The original driver and raw results remain local; its library revision and
driver hash are preserved. Their retention is not a claim that the raw new
journals are independently available or executed remotely. The temporary
experiment stop was removed only after its exit, restoring the exact prior
flags; this turn changed neither the existing recurrence nor ownership. Closing
readback found the existing automation ACTIVE at90minutes on this same chat;
the new mainline record describes a separate user cadence adjustment. It was
preserved, not overwritten with the earlier hourly setting.

## Exact homogeneous world

The vanilla mainline **forbids capturing Anchors and enforces royal safety**.
It does not currently express the suggested capture-Anchor-only game through
these ordinary RuleSet fields. This benchmark therefore explicitly uses the
existing royal game, rather than claim that variant was implemented.

Rules fixed before computation:

* 3x3; one Anchor and one ordinary actor per side, both with the same eight
  adjacent Leaper offsets. Anchor safety is an additional legality constraint.
* Alternating turns; no rays, drops, promotion, pass, declarations or auxiliary
  effects. Captures remove the ordinary victim from the game.
* No legal move while checked loses; stalemate draws. Second occurrence draws.
  The new RuleSet's **sixth completed half-move draws**, after mate/stalemate
  priority. This is an actual finite-game rule, not a resource-censor label.
* Fresh-start layout census requires both Anchors safe. All288 such ordered
  four-actor placements are included. These are layouts of one rule, not288
  independent rule families.

Every legal continuation of those starts was expanded, retaining **complete
GameState/history**, with no Position quotient. There are91,712 history
contexts and1,768 Positions (including turn); 11,328 nonterminal contexts have
children of different exact WDL. Overlapping/correlated histories are not
probability samples. Root outcomes are **80 first-player wins / 8 second-player
wins / 200 draws**. Terminal contexts include12,032 mates,6,560 stalemates,
4,704 repetitions and33,128 rule-clock draws. Expansion took8.364 s.

The existing Runtime threshold solver independently agrees on **every action
at all288 roots** (17,734 reference expansions,3.662 s). A separate full finite
transpose check covers all416 continuations of a selected start: legal action
bijections, resulting boards, turn, checking facts, repetition equality patterns
and terminal outcomes all commute. Static movement symmetry alone was not used
as a substitute for this check.

Public q0 search uses uniform material, fresh per-query TT, existing price-free
capture ordering,100,000 nodes/3 s per query. All1,440 requested root queries
completed their requested depth:

| Requested depth | Suboptimal WDL actions /288 | Paid nodes |
|---:|---:|---:|
|1|50|1,456|
|2|13|4,405|
|3|1|9,316|
|4|0|15,642|
|6|0|33,754|

At layout `[6,0,8,2]`, D3 selects ordinary `(0,0)->(0,1)`, whose exact value
is LOSS instead of the available DRAW. D4 avoids it. D6 buys no additional
root WDL quality over D4 on this finite census. This is not a general depth
threshold, equal-realized-cost comparison, or infinite-horizon solution.

## Why one very simple A/B world is degenerate

Keep the same layouts, counts and rules. A has four orthogonal one-step jumps;
B has four diagonal one-step jumps. They have equal target counts.

| Ordinary type of player0 / player1 | Complete H6 history contexts | Contexts with different child WDL | First-player W/D/L over288 starts |
|---|---:|---:|---:|
|M / M, eight-neighbour control|91,712|11,328|80/200/8|
|A / A|112,192|1,336|8/280/0|
|B / B|41,504|296|40/248/0|
|A / B|79,184|0|0/288/0|
|B / A|81,736|0|0/288/0|

All A/B and B/A reachable contexts are DRAW, not UNKNOWN. Increasing the new
rule horizon to10 on the first8 fixed layouts still gives all DRAW across
36,644 and48,846 contexts. The original H10 output's scope string mistakenly
said H6; its explicit horizon and ply counts are correct. That original is
retained, with this correction, rather than silently presented as H6 evidence.

A stronger test enumerates **every static placement** with both Anchors and
either, both or neither ordinary actor. It excludes a checked nonmoving Anchor,
which a legal preceding move cannot leave. It does not claim every enumerated
placement is reachable. Every actually reachable position belongs to this set.

| Board | Placements before legality filter | Admitted ongoing / stalemate | Checkmates | Time |
|---|---:|---:|---:|---:|
|3x3|8,208|2,736 /72|0|<1 s for all five3x3 controls|
|4x4|101,280|55,004 /76|0|1.807 s|
|5x5|663,600|445,744 /80|0|13.879 s|

Thus no strategy can win in this one-ordinary-per-side A/B domain on the checked
boards: all its other terminal rules draw. This conclusion uses terminal
exhaustion and rule semantics, not a heuristic zero score.

There is also a locality argument for square boards of size>=5. In a mate the
checking ordinary actor is within one square of the victim Anchor. The enemy
Anchor must protect that checker; otherwise the victim Anchor captures it.
Therefore the enemy Anchor is within Chebyshev distance two of the victim.
A victim ordinary actor farther than two cannot block an adjacent escape,
capture the checker in one jump, or block a Leaper attack, and may be omitted
for the mate-existence question. All relevant actors are consequently in a5x5
window. Distances0,1,or>=2 from each board edge have representatives in a5x5
board, preserving the local check and escape possibilities. Any larger-board
mate would produce an admitted mate in the exhaustive5x5 census, contradicting
its zero count. This is a written local-reduction argument backed by the finite
census, not a new symbolic proof checker. It applies only to these moves,
actor counts, royal legality and draw policies; capture-Anchor games are outside it.

## A legal composition counterexample

Start from the following safe board, with player0 to move:

| Rank | File0 | File1 | File2 |
|---:|---|---|---|
|2|A0|K0|empty|
|1|empty|empty|empty|
|0|K1|A1 or B1|empty|

Replay the SAME legal first move, A0 `(0,2)->(0,1)`, in three explicitly
constructed fresh RuleSets:

| Intervention | Result after that move | Exact player0 value |
|---|---|---:|
|Defender retains A1 at(1,0)|Checkmate|+1|
|Replace only that A1 with diagonal B1|Ongoing; B1 can capture `(1,0)->(0,1)`|0|
|Remove that defender ordinary actor at the fresh start|Ongoing; K1 escapes `(0,0)->(1,0)`|0|

The replacement preserves actor count and occupancy and changes geometry only.
The removal is a separate quantity intervention. Both have complete legal
histories and distinct correctly bound fingerprints; no old record was forced
into a changed rule. Additional defender material can be harmful by blocking
its Anchor's escape, while another four-target geometry supplies a defence.
The removal result is not a universal negative price for A.

An initial attempt to encode a checkmated board directly was correctly refused
by INITIAL_ANCHOR_ATTACKED / INITIAL_NO_LEGAL_MOVE. We retained that failure and
used the safe start plus actual move above. An earlier duplicate initial-setup
attempt was likewise rejected before any transition; neither validator was weakened.

## Parameters, policy regions and learning

Changing only B to eight-neighbour movement restores509 and247 genuine-choice
contexts in the two role variants on the same8 layouts. The following is a
POSTHOC mechanism diagnostic: first64 of70 preorder genuine-choice contexts
containing both ordinary types, not representative or held-out data.

Fix board-A=1 and vary board-B=r. Since actors cannot multiply, leaf material
scores are among `{0,1,-r,1-r}`. Pairwise crossings occur only at r=-1,0,1.
Within an open interval their ordering is unchanged; an ideal complete fixed-
tree minimax therefore has the same material-optimal action sets there.
This is a useful-parameter region, not an intrinsic-price identification.
Implementation ties, finite caps and near-boundary floating comparisons need
separate qualification. All recorded queries here completed.

| r | D1 WDL errors /64 | D2 | D3 | D6 |
|---:|---:|---:|---:|---:|
|-2,-1,-0.5, each|21|7|3|0|
|0|11|6|2|0|
|0.25 and0.75, each|11|7|3|0|
|1|10|6|2|0|
|1.25 and4, each|10|2|1|0|

All256 matched actions agree within each tested positive interval pair.
At D2, changing r=.25 to1.25 changes the chosen WDL in five contexts: four
draw-to-win changes and one loss-to-draw. At that last context, D1 with r=.25
draws but D2 with the SAME price loses. Intermediate-depth improvement is not
pointwise monotone. D6 reaches actual terminal leaves and is WDL-optimal for
all these prices; a particular tied move can still depend on earlier iteration
ordering, even when the exact best WDL set does not.

One small experiential check then uses the original TDLeaf(.95), eta.05,
scale10,initial r=.25, eight fixed starts, balanced candidate colors and the
same fixed uniform D2 foe. Candidate D1 and D6 each play32 episodes. The
120 s/2M-node ceiling was fixed before execution; actual cost is3.077 s/7,780
nodes. Exact values are observer fields added AFTER search, never evaluator,
ordering or TD inputs. It is a learning-process check, not another strength panel.

* D1:18 changed updates, r=.25 ->.3223368963. Re-querying every one of its
  74 candidate decisions with INITIAL weights gives the SAME action. The
  numerical motion stayed in(0,1) and did not change these32 trajectories.
* D6:78/78 candidate PVs are terminal; all material gradients and updates are
  zero. Four nonzero TD errors still occur, but multiply zero eligibility.
  Exact play needs no material coefficient inference here. A win does not
  automatically give this learner a usable gradient.

All64 histories,304 query action labels and64 updates were independently
checked with Runtime reference values and forward-lambda arithmetic (max
weight error5.55e-17). The original query field `weights` meant the candidate
snapshot for BOTH actors; its fixed foe is all-ones. That recording ambiguity
is preserved with an explicit correction; future source separates candidate
and searching weights. No original results were overwritten.

## One next scale already tested

At the SAME3x3/H6/repeat2 rules and fixed six occupied squares, each player now
has an Anchor and TWO ordinary actors. The centrally symmetric corner setup
is fixed before solving. Homogeneous MM, AA and BB are matched-count controls
for mixed AB on both sides.

| Own lineup, mirrored for opponent | History contexts | Mates | Genuine-choice contexts | Root WDL |
|---|---:|---:|---:|---|
|MM|1,651|166|113|DRAW|
|AA|2,629|92|142|DRAW|
|BB|259|0|0|DRAW|
|AB|1,151|14|26|DRAW|

Mixed AB restores mate possibilities and meaningful choices despite the root
being DRAW. This directly limits the one-ordinary theorem; adding actors is a
different intervention from changing board size. Over all26 genuine-choice
contexts, four positive ratios .25,.75,1.25,3 each make two D1 WDL errors and
zero D2/D3/D6 errors. Across .25 versus3, one action changes at D2, D3 and D6,
with NO WDL change. These416 new public queries do not select a price winner.
Both-side A/B coexistence is now a concrete reusable baseline for a later
matched-count replacement by C, not a completed A/B/C/D theory.

A final small C feasibility case has also begun, rather than leaving only a
plan: use eight centrally mirrored occupied squares, comparing ABA versus ABC
ordinary lineups on BOTH sides. C has only the two horizontal one-step leaps;
it replaces the extra A at the same squares, keeping total force and occupancy
fixed. The same H6/repeat2 rules solve in0.118/0.062 s:1,195 versus685 history
contexts,35 versus4 mates,50 versus6 genuine-choice contexts; both roots DRAW.
This establishes an executable, nondegenerate composition comparison. It does
not yet identify a changed A:B price region or a strategic advantage for C.

## Reusing expensive history: task2625

Historical revision `4d0fd6d4279e361927368ee656c9727d266ffb74` contains byte-exact
gzip archives for evaluation games/queries and training episodes/queries.
They decompress to the current local originals:3,022,370 /125,750,147 /
11,001,717 /347,717,914 bytes. The evaluation games retain SHA-256
`7426c7f8c1d5834a59dbd5992fcae1b19a4e05e6601e8412ccae9de0bc9123e8`.
The current tree retains summaries while these large originals are historical;
local byte equality and Git ancestry were checked, not independent remote execution.

Reanalysis of all1,024 games /512 pairs /22,305 saved queries confirms:

| Paired outcome | First divergence at candidate | First divergence at fixed foe | Total |
|---|---:|---:|---:|
|TDLeaf WIN / initial LOSS|49|37|86|
|TDLeaf LOSS / initial WIN|16|17|33|

Across the whole panel,190 first divergences occur at the fixed foe with
identical history, weights, requested nodes and complete search root value.
The frozen evaluation source explicitly adds `(endpoint == "TDLeaf")` to its
random ordering seed. Thus fixed-foe identity does NOT provide a matched random
tie schedule. Existing finite endpoint outcome bounds remain descriptive, but
these flips cannot all be attributed to a pure learned-weight intervention.
This is a new source/trajectory mechanism observation, not a rerun or a claim
that either split action is exact-WDL optimal.

Four lexicographically first positive/reverse, candidate/foe examples were
selected AFTER outcomes and24 full game/split-prefix records strictly replayed.
For example `[271001,1977,4000051,0]` first splits at foe ply7: both root values
are0, but X drops at(1,0) versus(3,0), followed by opposite real outcomes.
`[271001,1977,4000054,1]` reverses the outcome sign after a foe split at ply0.
These are mechanism examples, not independent validation samples.

Available: full chosen trajectories, real terminal/UNKNOWN labels, pre/post
weights, query costs/completion, selected PV features/values and training
updates. Missing: complete PV ACTION paths and all alternative action values.
Consequently saved logs cannot certify exact optimality at the divergent move,
reconstruct every searched tree, or establish a causal weight effect without
new explicitly controlled computation. No such computation was disguised as reuse.

Task2620's evaluation histories and compact receipts remain in Git at
`e6368f3c67ad386d5f10dac81355175cc05a4abf`; their location was checked, but
no new full reanalysis was claimed. Recent natural-rule raw trajectories and
models remain local. PRIMARY's published HAND_VALUE_CONTEXT_AND_SEARCH_COST
report was read at6ea35571 and reused for the distinction between coefficient,
value, ordering, cost and policy equivalence; its experiment was not repeated.

## Reproduction and next question

`scripts/leaper_microgames.py` provides the rule constructors, finite unroll,
public decision studies, static census, legal blockade example and bounded
learning diagnostic. `scripts/reuse_tdleaf_pairs.py` reads the historical
compressed originals directly and refuses a differing local trace. Neither
imports old audit/registration machinery. Use fresh output directories:

```powershell
.venv\Scripts\python.exe -m scripts.leaper_microgames artifacts/leaper-reproduction --layouts 288
.venv\Scripts\python.exe -m scripts.reuse_tdleaf_pairs artifacts/paired-reproduction
.venv\Scripts\python.exe -c "from scripts.leaper_microgames import learning_diagnostic; learning_diagnostic('artifacts/gradient-reproduction')"
.venv\Scripts\python.exe -m pytest tests/development/test_leaper_microgames.py -q
```

Current science is OPEN. The next useful question is whether A:B policy/value
regions change in the now costed ABA-versus-ABC matched-count case. Preserve quantity/occupancy controls,
negative cases, history and the exact/finite-search/UNKNOWN distinction. There
is no requirement to fit a unique price, add a feature network, or enlarge the
old strength panels before taking that next step.
