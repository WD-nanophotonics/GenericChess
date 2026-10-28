# Representation invariance needs separate game and evaluator contracts

Status: active scientific checkpoint; this is not an ended60-minute segment.
Source sandbox d91928c548d3a69c83260adfd4198447c69125a4; new Pro0605JST,
blob84a17d95ccce5f1b2648d900995a2b1e8add8a3f, read and adopted. Shared
rules/search/terminal/history/product tests have no delta from31060392.
No Player, engine root search, WDL solver, game campaign, training or build.
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
