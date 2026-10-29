# Representation invariance needs separate game and evaluator contracts

Status: segment4baedcf3 ENDED; session finish accepted2026-10-29T00:14:45UTC.
3737.699354confirmed seconds minus120reserve=60.294989effective minutes;27distincttestsPASS. Earlier statements below describe their checkpoint scope.
Source sandbox d91928c548d3a69c83260adfd4198447c69125a4; new Pro0605JST,
blob84a17d95ccce5f1b2648d900995a2b1e8add8a3f, read and adopted. Shared
rules/search/terminal/history/product tests have no delta from31060392.
Initial source-only subquestions used no Player/search. The separately prospective
two-call control below later ran exactly twice; no WDL solver, game campaign, training or build.
No new normalizer, default profile, cache or TT change.

The new result is a limitation of the EXISTING legacy-reachable profile
control, not another reproduction of the previous UNUSED declaration.
A separate real repetition counterexample shows why geometric aliases cannot
automatically define the equivalence that an evaluator should respect.

## Input-domain contract and existing coverage

| Question | Existing authority | Consequence for this work |
|---|---|---|
| Which types enter legacy normalization? | profile.py examines base/current, positive hands, all setup positions, eligible base promotion sources | Reuse it; do not claim missing setup/promotion handling |
| Can a promoted target itself promote? | existing non-chain and independently-present-target tests | Reuse the distinction, no duplicate matrix |
| Can captured promoted actors restore base promotion? | existing capture-to-hand/drop branch | Keep base/current/promoted and both owner masks; no stock deletion |
| Does no-drop mean hands are semantically absent? | existing test_inert_hand_profile declaration/effect controls | No; retain hands and histories |
| Does semantic footprint certify legacy profile reuse? | prior actual create/newquiet-IR counterexamples | No; do not strip IR or substitute inspection handles |
| Can an alternate setup create new inventory? | compiler.py validates multiset(owner,base,current,promoted) | Our first illustrative X-start is invalid, retained as a rejected input |
| Does conservative closure equal exact executable reachability? | deliberately ignores some promotion-square feasibility | No; new actual counterexample below |
| Do equal current actions/values prove full-history equivalence? | typed repetition identity and actual24-ply trace below | No |

GitHub Pro is the independent direction review. Dot1793227713 is a solicited,
source-only critique: existing coverage, three-domain distinction and narrowing
were adopted. Dot did not execute Core/tests. Its additional request for renewed
user approval does not override the user's standing execution correction;
costs and closed caps remain recorded, with no expanded role or rollout.

## A dead promotion changes even the legacy-reachable profile

Before outcomes, literal 4x4 inputs and protocol were fixed in
promotion-inputs.json.gz (uncompressed SHA256
c4278563f794de9ad8f5d6e60227eb14efc9515add863e8e2b9403276ea2d917).
K is an ordinary eight-neighbor royal. P uses Leap(1,1).
There is one owner0 P at(2,2), K0 at(0,0), K1 at(0,3).
The decorated rule adds X with Leap(1,0)/Leap(0,1), declares P promotable to X,
and permits only owner0(2,2)->(3,3), owner1(1,1)->(0,0) promotion pairs.
Neither is forced. Drops are all false, capture removes actors, maxply32,
fourfold draw, no effects/aux/declarations/other initial setups in this pair.

Every declared owner/destination has ZERO X empty mobility in that owner's
frame. Core filters each such promotion variant. The actual evaluator's
promotion-zone sets are also empty. X starts absent and cannot be created:
ordinary moves preserve types, captures remove, no drops, and every possible
P->X variant is suppressed. By induction X remains absent along every legal
history. Existing K/P active IR patterns match modulo18 explicit pattern IDs
(14 actually change); geometry matches. New X board patterns cannot bind.
Disabled drop patterns have reindexed geometry and are not claimed byte-equal.

This is a structural argument for this exact pair. Complete finite two-ply
controls independently replay13 prefixes/12 paired edges per route, legacy and
semantic:48 direct paired-edge submissions plus32 prefix-replay submissions,
80 total Session.submit calls in the final reader. Internal Core legality
probes are not counted as Session.submit and their primitive count is UNKNOWN. Each prefix preserves
board/hands/actor/ply/terminal, action multiset under the actual map, and the
entire repetition-count bijection. The finite check supports but does not
replace the induction. No full game tree or minimax WDL was solved.

| Item | Original | Decorated |
|---|---:|---:|
| Legacy support | K,P | K,P,X |
| P raw capability |0.5782705269607844|0.5782705269607844|
| X raw capability | absent |1.4554137323943663|
| P board value |1000|569|
| P hand diagnostic |900|512|
| P promotion gain diagnostic |0|862|
| Active promotion zones | none | both empty |
| Actual ongoing root raw score |1002|571|
| Root legal actions |4|4|

Semantic-default profiles give the same corresponding numbers here.
The root dynamic contribution is2 in both; the price change is a conservative
normalization-support effect, not a realized promotion bonus.
The diagnostic hand/gain entries are not true strategic prices or reachable
inventory claims. The old profile builder was intentionally conservative;
this is not evidence of an implementation violating its current contract.

The first run failed on a THIRD illustrative alternate setup that added an X.
Compiler's INITIAL_SETUP_INVENTORY_MISMATCH was correct. The frozen input was
not replaced; both routes record its rejection, and only the unchanged valid
base/dead-promotion pair supplies the counterexample. The initial expectation
that setup was legal was ours and is corrected. A consumer typo using the
source geometry table while filtering decorated patterns was also caught by
a semantic regression and fixed; no product source changed.

## Identical geometry and values can still conceal different repetition games

A second literal 6x6 control fixes K0 at(0,0), K1 at(5,5), and two owner0 A
actors at(2,2)/(3,2). A and K each use eight-neighbor Leap geometry.
The decorated rule relabels only the second A as B with IDENTICAL movement.
No actor is split or added. No promotion, drops, creation, auxiliary state,
declarations or pass. Capture removes; maxply64 and fourfold repetition.

Four own moves exchange the actors via two empty cells:
(2,2)->(2,3), (3,2)->(2,2), (2,3)->(3,3), (3,3)->(3,2).
The distant enemy anchor shuttles(5,5)<->(4,5) after every own move.
This8-ply schedule is fixed for three repetitions before execution.
Actual Core legacy and semantic routes both verify all24 plies per rule:
96 transitions, all prior legal-action multisets mapped by full coordinates,
and all prefix raw evaluator values equal. Ordinary prices all remain1000.

At ply8, two distinct colored positions first project to the same original
position. At ply24, original current count is4 and Core returns REPETITION;
colored current count is2 and Core remains ONGOING. Full records/count maps
are retained. Neither rule is a solved DRAW/WIN game; these are actual outcomes
on one specified path. Equal values do not prove game equivalence.

Let f forget B->A. If a colored history projects move by move, the source
count of position x equals the SUM of colored counts over f's fiber.
The actual draw predicate is any count >= L, not a sum over forgotten labels.
A many-to-one projection can therefore reach a source repetition threshold
without any colored key reaching it. Injectivity on relevant reachable
repetition identities is a sufficient safeguard; it is not claimed necessary
for every finite cap or special adjudication. Merely transporting current
board/actor or summing counts is not preservation of the rules' predicate.
Continuous-check, no-progress, declarations and other history readers need
their own preserved observations; no stronger monotonicity theorem is used.

## Safe interpretation and next decision

Three requirements stay separate:
1. Game relation: complete start domain, two-way actions, terminal/declaration
   observations and every actually read history fact, including repetition.
2. Evaluation relation: corresponding relevant board/hand/promotion/dynamic
   terms, config, normalization support and rounding/clamp policy. Full extra
   diagnostic dictionaries need not be equal.
3. Caller/cache relation: actual compiler/evaluator route, config/version and
   compatible lifetimes. Equal fingerprints across compiler forms do not waive
   existing cache namespaces; different fingerprints never share TT identities.

This work rejects the broad assertion that the existing reachable-type builder
solves all representation invariance. It also rejects automatic merging of
same-geometry labels into a game quotient. No replacement normalizer or
automatic universal reachability classifier is delivered. The concrete
decision is to require an explicit invariance policy in cross-rule comparisons
and preserve UNKNOWN when either game or evaluator contract is unestablished.
These source/cost boundaries are useful without claiming chess strength.

Six targeted regression cases pass after fixing the consumer typo and using an
own-checkout pytest temporary directory (the system temporary directory denied
access). Original failed test receipts remain private. This checkpoint includes
no re-execution of old timing/Native/H6 experiments or PRIMARY's new quality
panel. Current ordinary session still needs its own60+effective-minute ledger.

[Promotion observations](data/aux_representation_contract_20261029/promotion-observed.json.gz)
and [history observations](data/aux_representation_contract_20261029/history-observed.json.gz).


## A stronger but narrower decision statement for THIS one-P pair

A further decision-changing check asks whether the new dead-promotion raw
difference can alter an exact complete finite-backup preference at all.
There is at most one owner0 P, no ownership change or hand production, and two
preserved K actors. Its current inventory count c is0 or1. Let d be the common
seat0 dynamic contribution; old/new values are1000c+d and569c+d.

A source-derived conservative envelope is |d|<=122:
mobility<=16*2=32; escape difference<=8*5=40; and the two check indicator terms
combine to at most50, not100. All promotion zones are empty, and hands remain
empty. Thus the nonterminal value supports lie in:
old [-122,122] or[878,1122], new [-122,122] or[447,691].
These bands are disjoint in the SAME order. Raw static clamping is inactive.
Actual matched terminal scores are0 or +/- (MATE_SCORE-ply); maxply32 leaves
their nonzero magnitude at least999999968, outside both bands.

One common STRICTLY INCREASING seat0 function f is identity on the low band
and terminal bands, and subtracts431 on the high old band; positive linear
pieces connect the gaps. Exact Fraction arithmetic checks all556 overapproximated
integer static/terminal values and555 adjacent order relations, not556 game
states or labels. Because min and max commute with a strictly increasing
function, every node's value on the SAME finite complete tree/frontier maps
by f. Root argmax sets AND ties therefore remain identical by induction.
Actor-centric negamax must first be interpreted as seat0 min/max; f is not
assumed odd.

A separate exhaustive finite static input check evaluates all7200 assignments
of K0,K1 and optionalP0, including both actors, PER compiler route.
Across the two corresponding evaluators this is14400 calls per route,28800
total. Many assignments are unreachable or illegal game positions; this is a
position-only evaluator envelope check, not Core/game/WDL enumeration.
Observed dynamic ranges are[-35,35] without P and[-40,87] with P; the proof
keeps the conservative122 bound and does not claim these as reachable extrema.
All paired raw values differ by exactly-431c.

Practical consequence: the raw invariance counterexample is real, but this
particular one-P pair cannot by itself demonstrate a changed exact complete
fixed-frontier choice. A paid complete-tree root comparison merely seeking
such a difference is unnecessary. This DOES NOT establish equal actual
fixed-service retained Player decisions: setup cost, ordering, selective
margins, visited frontier, Q policy, TT lifetime and cancellation can differ.
It does not apply to the prior A/B/C counterexample or type-merging pair.
No new Player/root search was used to prove this statement.

[Order embedding](data/aux_representation_contract_20261029/order-embedding.json.gz)
and [finite static envelope](data/aux_representation_contract_20261029/static-envelope.json.gz).


## Averaged heuristic signals are a different contract

The monotone min/max result does not imply invariance of expectation.
Three fixed actual4-ply histories from the SAME original/decorated game pair
supply final seat0 surrogate values -21/-21, -35/-35 and1002/571.
Both compiler routes replay all prefixes, preserving full repetition counts,
and every final state remains ONGOING atply4. These48 Session.submit calls
are literal contract trajectories, not engine matches or terminal labels.

Compare a deterministic specified continuation with value-21 against a
DELIBERATELY specified mixture:47/48 of the -35 continuation and1/48 of the
1002/571 continuation. These two branch protocols use legal histories from the
same root; they are not an observed uniform or optimal opponent distribution,
and they do not cover all root choices. The probability is a constructive
mathematical choice, not an estimate or tuned training policy.

| Surrogate | Deterministic | Mixture expectation | Mixture minus deterministic |
|---|---:|---:|---:|
| Original |-21|-643/48|365/48 >0|
| Dead-promotion |-21|-179/8|-11/8 <0|

For an explicitly ILLUSTRATIVE tanh(score/1000), the same ordering flip occurs:
original mixture -0.01837283 beats -0.02099691; decorated mixture -0.02350490
does not. This scale is not the maintained learner's configured scale.
A strictly increasing non-affine transform commutes with min/max, but generally
not averaging. Positive affine transforms preserve arbitrary expected-utility
orders; arbitrary ordinal transforms do not. This changes a truncated
heuristic-expectation objective, not expected actual W/L/D. Matched terminal
payoffs/distributions remain unchanged under the exact game relation.

The actual maintained AUX learner was separately checked at its REAL consumer:
incremental.compile_channels uses board CURRENT/hand BASE features and a fixed
declared board unit; Model.raw and prediction use explicit model weights and
scale. mainline_search.Material supplies an override and equal capture priority,
not the default generic-v5 profile. At these same histories the P-unit feature
is1 or0, all hand features are0, and the added X board/hand channels are0.
Mapped explicit models therefore give identical material raw values/predictions.
The checked scale10 model returns tanh(0.1)=0.09966799 when P remains.

More strongly, THIS one-P fixture offers zero free material gradient to this
fixed-P-unit model: the only nonzero board feature is the fixed unit, whose
gradient is explicitly0; every free feature stays0 by the same inventory
induction. All traced read-only gradients are0 in both representations.
TDLeafEpisode's eligibility sum would remain0 for any such episode, including
actual constant terminal leaves or censored final UNKNOWN, provided the declared
fixed model/feature contract is retained. No observe, finish, apply or training
function was called to establish that algebra. This is not a statement that
all value classes or other games cannot learn. It is a concrete reason NOT to
use this normalization fixture as a relative-material-learning success test.

Neither the generic surrogate expectation flip nor zero-extension identity is
a demonstrated learner bug, model improvement, actual root-choice flip or
permission to train on labels. Existing model/unit/scale metadata remains the
authority; matching seeds alone would not certify matched explicit controllers.

[Fixed legal mixture inputs](data/aux_representation_contract_20261029/expectation-inputs.json.gz)
and [actual prefixes/read-only learner observations](data/aux_representation_contract_20261029/expectation-observed.json.gz).


## A separate coordinate-frame policy, with equal material profiles

One additional restricted4x4 input uses K's eight-neighbor Leap, P's
Leap(0,1), and promotion target G with K-like mobility but non-royal status.
K0=(0,0), K1=(3,3), P0=(1,1). Only P0(1,1)->(1,2) and the owner1 counterpart
are promotion-enabled; none forced. Drops are false, captures remove, fourfold,
maxply32, no effects/aux/pass/claims/setups. The second rule rotates EVERY board
square R(x,y)=(3-y,x), relative movement vector(-dy,dx), and actual promotion
mask pair. Owner identity stays fixed. R commutes with owner1's180-degree frame.

The literal inputs were frozen before execution at SHA256
4da324c62dd492cd38e4873cfd570d9d98c8dd6f577ef54913b3fa3bb23ebac7.
All96 owner/type/source mobility rows per route map exactly. Semantic pattern
bodies and complete geometry paths are explicitly rotated and rebound.
The first own comparison omitted path-table reindexing, failed, and was fixed;
the frozen rule pair was not replaced. Two-ply Core action/count/terminal
bijection covers15 prefixes/14 paired edges per route:56 direct submissions
plus40 prefix replays,96 Session.submit calls over legacy+semantic.

Both profile tables are IDENTICAL: P273, G1727, K0; promotion gain1454.
Yet actual root value is271 versus270. With promotion_potential_weight=0 both
are270. The source P has a rank-forward approach to its real promotion zone
and bonus1; the rotated west-moving P has no rank-forward destination and
bonus0. The zone itself and legal promotion option were rotated correctly.
All other raw terms match in this control.

The code explicitly defines owner0 forward as +rank and owner1 as -rank.
It does not promise90-degree evaluator covariance. We therefore report an
additional POLICY distinction, not a violation of an existing product promise,
unsafe legality, material-price mismatch, root-choice loss or a fix request.
A full game-coordinate isomorphism need not preserve a heuristic feature tied
to a preferred coordinate axis. Existing180-degree owner-swap symmetry tests
are a different property. No normalizer, canonicalizer or production feature
was changed.

One positive regression and one corrupted-promotion-mask negative control
ensure that equal rotated movement tables cannot substitute for the actual
promotion/action/history relation. The corrupted mask leaves stock/movement
and normalization support unchanged but fails the Core action mapping.
The total relevant regression set now has13 distinct passing cases.

[Rotated literal inputs](data/aux_representation_contract_20261029/rotation-inputs.json.gz)
and [Core/profile/feature observations](data/aux_representation_contract_20261029/rotation-observed.json.gz).


## Captured stock: equivalent restricted play does not mean identical learner channels

Source remains sandbox48749ec334c9eb42955a844f06e1d101bb2a02e2.
The separate frozen stock input SHA256 is
815837e0a1e70ca9ef2aef9ad6bb10e491bddf275838b60291837f02a88e8f4f.
Change ONLY capture removal to capture-to-hand on the earlier4x4 one-P game;
all drop masks remain false, no promotion/creation/owner changes/DSL/declarations
or alternate setups. This is a scoped game relation, not general stock deletion.

Let B_i(t) count surviving BOARD actors of BASE type t owned by i, N_i their
initial counts, and H_i(t) their hand counts, initially zero. With ordinary
opponent capture-to-hand, no drops, creation, base-type or owner changes:
H_0=N_1-B_1 and H_1=N_0-B_0. An ordinary move changes none; promotion preserves
base and owner; a capture removes one opponent base actor and adds that same
base to the capturer's hand. Induction proves the relation. In signed features,
h=H_0-H_1=(B_0-B_1)-(N_0-N_1). This is an AFFINE reachable-domain relation.
It is not a claim about arbitrary externally supplied hands. With a drop by
seat s, signed h decreases s while signed B increases s; h-B changes by -2s.
Hand readers, resource claims/effects, owner/base changes or arbitrary initial
stock require a different proof. Promotion is allowed in the base-count identity
but not in a substitution of CURRENT-type board features for base counts.

For the frozen one-P game, h_P=p-1, p in{0,1}. The full typed board uniquely
determines the extra hand, so the projection is injective on this reachable
domain. Root clocks/side and every later clock match. Ordinary move/capture
authority and royal safety cannot read this inert stock; typed repetition keys
correspond bijectively. Thus entire repetition-count maps transport, not just
the current board. A16-ply actual capture-plus-three-cycle trace per rule and
compiler route checks17 prefixes and an8-key map, ending in literal fourfold
DRAW at ply16 on both.64 Session.submit calls total. It is one trace, not
solved WDL or proof by finite enumeration. No Core/TT identity was replaced.

The actual maintained learner uses CURRENT board type counts and BASE hand
counts. With fixedP=1, scale10 and initial free hand weight w=0, feature vectors
are(p,0) for removal and(p,p-1) for retention. At ongoing ply4 after capture,
both predict0, but free-hand gradients are0 and-0.1 respectively.
No-drop therefore does not imply a zero free gradient. Terminal observations
are literal WLD constants with zero gradients; the final trace DRAW does not
become a material label. No observe/finish/apply/training was called.

Nor does the affine relation establish redundant parameters in this model.
The retained model has raw p+w(p-1)=(1+w)p-w. Its fixedP anchor and lack of a
free intercept mean w changes the missing-P baseline while keeping p=1 pinned.
The one free feature varies across p=0/1 and is not identically zero; calling
this two-channel fixed-anchor model rank deficient would be wrong. An added
intercept or separately free board coefficient would define a different
parameterization. Any fitted w would conflate this board/baseline relationship
with stock; it would not identify an independently manipulated causal hand price.

A useful negative consequence follows WITHOUT training: on the literal recorded
current-state sequence, every p=1 observation has zero free gradient, every p=0
observation has prediction0, and after capture p never returns to1. All later
current-state predictions and the literal final DRAW target are0. The frozen
TD(lambda) sum therefore has zero update for any eta/lambda: transitions that
can have nonzero errors have zero accumulated eligibility, while transitions
with nonzero eligibility have zero error. This is an algebraic CURRENT-STATE
trace control, NOT an actual search/PV training run. A different sequence with
nonzero terminal WLD, different PV features, nonzero initialization, or additional
free types can change the conclusion. Nonzero gradient alone is not a reason
to launch a training campaign on this fixture.

The promotion boundary uses the existing P->G rule, capture-to-hand, and four
actual legal moves: P(1,1)->(1,2)=G, enemyK(3,3)->(3,2),
G(1,2)->(2,2), enemyK captures at(2,2). Both compiler routes agree: after
promotion CURRENT P=0, BASE P=1, handP=0; after capture handP=-1 and handG=0.
Thus hP=currentP-1 already fails at the promotion prefix although the base
conservation identity remains true.8 actual submissions in this new boundary.
Inputs, records and exact feature rows are in stock-promotion-boundary.json.gz.
The scoped admission test rejects even one enabled drop square, including a
configuration whose root happens to have no current stock.

## Actual two-call tie control, now CLOSED

The prospective protocol was published at987598df443f4ef922093b1d8e6183c06dc6e17c
before dispatch. Frozen input SHA256
e205b644743d73a0c4e3ddd840122660068793eb4aeba40cd6053aebe6d210dd.
Exactly TWO cold public AlphaBetaPlayer calls ran once; the lifetime cap is
EXHAUSTED. Both returned complete main_iteration D1/Q0 score2000,18nodes,
0qnodes,17evaluations and balanced17push/pop. Each had3s whole-call allowance,
including compile/constructor/choose/pack; observed walls0.0078719/0.0071813s.
The whole experiment wall0.142707s and CPU0.15625s include preflight; clock
granularity and one exposed control forbid speed comparisons.

The bijective type rename K->K,A->Z,B->A preserves the game, completeD1 values
and17-way argmax. Original picked A(2,2)->(1,1); renamed picked A(3,2)->(2,1).
The mapped original would be Z(2,2)->(1,1). Both actual choices belong to the
mapped argmax, but literal returned-action equality is false. Existing ordering
sorts str(action); root best replacement requires strict score improvement.
This explains a representation-dependent tie choice, not quality regression.
The game/history preflight checked65prefixes/64paired edges/222submissions;
a separate pre-dispatch preflight also ran and is additional cost, not hidden
inside that count. Postdecision PV checking adds2submissions.

The offline reader verifies frozen/dispatch/result binding, both distinct slots,
complete metadata, mapped argmax membership and the computed equality flag.
Tests NEVER call the exhausted producer. Four corruption cases reject false
bindings, duplicated slots, unmatched actions and fabricated equality. Three
new stock tests and this reader's five cases PASS:8new cases,21distinct cases
across this round including13earlier cases, not21independent experiments.
The two raw returns and dispatch receipt are packaged in the manifest.
No product, model weights, defaults, new game campaign, solver or training changed.

Receipt correction: the executed producer left its legacy remaining_slots field
as NOT_RUN even after both successful calls. Preserve that exact raw field;
COMPLETE plus the two distinct call receipts establish exhausted slots. The
offline reader reports the stale field explicitly, rather than silently
rewriting the original or treating it as an unexecuted slot. The executed
producer source remains pinned in987598df; no producer rerun was made.


### Why the stock affine relation is not a free monotone-search theorem

The exact retained-stock trace has the same material features(0,-1) at ongoing
ply4 and terminal fourfold-DRAW ply16. The underlying typed board/hand/actor
returns after each four-ply cycle; history/counts and clock differ. The learner's
terminal authority overrides material and returns literal0 at the latter,
with zero gradient. For a symbolic nonzero hand coefficient w, the ongoing
material raw value is -w while the terminal draw stays0.

Even when w>-1 preserves the ordering of the two NONTERMINAL inventory bands
(p=1 raw1 versus p=0 raw-w), that alone does not supply a single strictly
increasing transformation of the OLD complete-frontier values. The old missing-P
nonterminal value and terminal-DRAW value both equal0; their proposed images
-w and0 differ unless w=0. A function cannot map the same argument to two
different outputs. This blocks an attempted reuse of the earlier dead-promotion
minimax embedding. It does not establish an actual changed root decision:
no common decision frontier containing both histories has been shown or queried.
The distinction is terminal calibration/history aliasing, not an independently
identified hand price. We did not initialize, fit or tune w in any real learner.
