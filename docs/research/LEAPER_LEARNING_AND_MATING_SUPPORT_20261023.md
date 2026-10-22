# Learning, mating support and capability boundaries

DEV_AUX uses committed sandbox infrastructure
`06c7eb414b0ec8993f5d3d90606e8fcba36ff9d7` and the maintained learner at
`b0c48c5cc388528171a40fd90d6d92d201ec653e`. PRIMARY owns rule/opening generation,
forward screening and inverse proposals. This work consumes its frozen rules
and histories; it changes no engine, evaluator, sampler or product default.

## Actual learning: a small gain reaches the free prior

The frozen cohort is the next eight SHA256(`AUX-episode-cost-v1:`+fingerprint)
entries in the original 50 corner-layout rules, excluding the previous ONE
preflight. Both roles are retained. Selection uses metadata only, without
mate/deadzone/WDL/price filters. This is an exposed corpus, not a held-out panel.

Sixteen zero-update consumer episodes finish in 33.367 seconds: 551 complete
D4 queries, 113,943 nodes, no missing slots. All 2,096 literal PV edges and full
histories replay. There are 276 candidate observations but only eight nonzero
TD error-times-eligibility terms across four episodes. Two terms have zero
current gradient but nonzero carried eligibility. Actual terminal TD terms are
zero; searched terminal information can nevertheless arrive in an earlier
bootstrap transition. A zero instantaneous Jacobian is not a zero trace.

Exact old-history joins find no matches among the 528 distinct new roots.
Reusing immutable COMPLETE graphs, without expansion, separately labels 332
of the 551 new visits: 94 forks, six inferior choices and 149 structural draws.
Only three of the eight nonzero candidate terms have coverage; all three
preserve WDL, one at a fork. The other five remain UNKNOWN.

The next, separately frozen pilot uses all eight rules, 16 training episodes
per rule/initialization, alternating roles, eta .05/lambda .95/scale 10. The
opponent is always frozen mobility-material D4. It reuses the 16 unit controls,
executes 16 mobility controls, 256 TRAIN episodes and 32 frozen endpoint EVAL
episodes. All 304 new slots finish in 209.333 seconds under the 1,200-second
whole cap. The consumer uses 8,192 nodes/query, 128k nodes/180s per episode,
5s/query and PV reserve zero. No oracle enters experience or start selection.

| Candidate against frozen mobility D4 | W | D | L | UNKNOWN | EVAL nodes |
|---|---:|---:|---:|---:|---:|
| Unit, no training |4|7|5|0|113,943|
| Unit + TDLeaf |4|8|4|0|54,750|
| Mobility, no training |4|8|4|0|35,860|
| Mobility + TDLeaf |4|8|4|0|35,860|

Unit training changes one LOSS to DRAW, a finite paired signed-utility gain
of 1/16; the other 15 results stay unchanged. It matches the free prior on all
16 endpoint outcomes. Prior training changes none. These are exact panel
differences, not population confidence intervals, Elo or superiority to priors.
The repeated deterministic games are not independent samples: the 256 TRAIN
episodes have only 14 distinct complete records.

Training pays 488,175 nodes/122.182s from unit and 286,880 nodes/57.962s from
mobility. Equal episode counts/caps do not mean equal actual search cost.
There are 18 and 16 nonzero updates respectively, all from bootstrap terms;
actual terminal credit is zero throughout. Hand channels remain unreachable.
Full replay and independent arithmetic check every update and weight chain.
Across the whole new cohort plus pilot, there are 320 physical episodes,
4,748 queries and 1,015,468 nodes. Reused controls are counted once.

The rescued [18,26] world moves B from 1 to 1.0331536846809253 after its first
loss. Its unit role-0 game changes from a 122-ply loss to a 16-ply rule draw.
All four endpoint action divergences, across [18,26] and [20,24]/both roles,
occur at D4 ties. Literal Fraction/Core enumeration (6,827 visits) verifies
strict argmax reductions of 2→1, 2→1, 4→2 and 2→1. This diagnoses a boundary
crossing; it does not prove the six-actor root's game-theoretic WDL. Numerical
drift in [9,23] changes neither paired endpoint trajectory nor outcome.
Close this pilot rather than extending these deterministic training paths.

## Exact single-piece mating support

Using PRIMARY's unchanged complete RuleSets, enumerate all nonoverlapping
K/K/(optional X) placements, either X owner and either mover, rejecting a
checked nonmover through Core. These are **constructed fresh states**, not
claims of reachability from the six-actor opening or GameSession replays.
The graph is closed under actual Core transitions, capture removal and no
promotion/drop. Attractor ranks certify decisive fresh games before clock 128;
draw strategies remain safe when repetition-four or the clock ends play.
This is not a general history quotient.

All 31 4×4 geometries close: 229,672 attributed graph vertices,
168,549 reused transitions/vertices and 61,123 newly expanded vertices in
58.711s. Sums contain repeated lower-material vertices across graphs.
Owner flip, rotation and reflection preserve every vertex, edge and label.

Exactly 11 masks have **no mating terminal anywhere** in this admitted domain:
1, 2, 4, 6, 8, 9, 16, 17, 18, 20, 22. Their KX subgames are structurally dead,
not merely minimax drawn. Each other mask admits a nonterminal forced WIN.
Within this fully enumerated 31-mask/4×4 domain, mating existence is
equivalent to containing one of the five minimal orbit subsets 3, 5, 10, 12,
24. This is an exact finite Boolean description, not a fitted quality score,
a natural frequency or an intrinsic piece price.

The five geometries actually frozen in PRIMARY's latest 5×5 packet
(1,2,3,4,8) also close: 198,896 attributed vertices, all newly expanded, in
104.433s. Single orbits 1/2/4/8 still have no mating terminal; King-like 3
does. Its maximum decisive rank is 16 rather than eight on the 4×4.
This compares the constructed rule kernel, not the profile-changing forward
games or equal-cost player strength.

## More capability can turn WIN into DRAW

Compare all 75 single-orbit additions on common admitted 4×4 KX
positions, keeping the physical arrangement and mover fixed. Among 505,928
overlapping comparisons, 139,344 improve X's WDL and 4,896 worsen it. Thirty-five
of the 75 inclusions have at least one worsening. Of those worsened positions,
4,776 become immediate stalemates and 120 remain ongoing in both rules.
These are an exhaustive finite comparison table, not independent observations.

A literal example has strong K on b1, weak K on d1, X on b2, weak to move.
With King-like X (mask 3), weak K must move d1→d2, then X can mate: rank two.
Adding the distance-two orthogonal orbit gives mask 7. X additionally controls
d2 while not checking d1, so the same legal arrangement is already stalemate.
No history, price or search limit creates this reversal. A second witness,
mask 25→29 with strong K a1/weak K c3/X d4/strong to move, changes rank-15 WIN
to DRAW while both roots remain ongoing.

Initial placements and absent-piece metadata differ between the frozen source
RuleSets, but cannot enter these closed KX/remove-only subgames. Full Core
closure and the solved certificates bind the active geometry and terminal
semantics. The counterexamples do not claim that an orbit edit is behaviorally
small or that stronger movement generally harms play.

## Latest 5×5 natural histories

The new input is PRIMARY's 224-game opening-response packet at fixed source
06c7eb41, compressed SHA256
`d5d4df3b3c88246caf16c87c82993e5c136a83a6ac0ea864d8d8fa5c132a93b3`.
Only its 32 completed 5×5 games supply the new four-actor observer.
All 1,799 distinct histories across 12 material components are retained in a
roster-round-robin manifest. The fresh 1,500-second whole/150-second component/
300k-state caps do not reopen any old 4×4 cap. COMPLETE exact-fingerprint
5×5 single-piece graphs are reused only for material subsets; partial
graphs, costs, labels and unattempted components remain distinct.

All 12 components are attempted; nine close and three hit the 300k-state cap.
The batch closes in 971.279s with 1,793 labels and six missing histories. Its
2,069,718 summed vertices include 900,000 in partial graphs and repeated lower
material across components; they are not globally unique states. There are
279,712 reused vertices, 1,644,188 new expansion attempts and 1,644,185 completed
new expansions. All three partial graphs are preserved. Nothing is resumed.

Every labelled root is DRAW with no observed WDL fork. Of these, 600 are
structurally dead and 1,193 are unblocked minimax draws despite reachable
cooperative mates. A separate decomposition finds no clock/repetition-induced
draw suppression among this known subset. Completion is informative censoring:
five of the six missing histories belong to [1,3], the code responsible for
PRIMARY's material-response gain. The other belongs to [4,8]. The completed
subset cannot establish that all 5×5 natural play lacks useful signals.

A separate existing Session proof-number control accounts for all 12 planned
target slots on the six missing roots: ten actual calls and two logically
skipped opposing targets after verified wins. It pays 122,908 proof-tree nodes
and 31.007s in the proof/control phase, producing four independently replayed
winner certificates (36 certificate nodes), with one target-flip corruption
rejected. Two roots remain unresolved; four calls hit their 30k-node limit.
These positive bounds are separate evidence, not replacement labels or action
coverage for the capped graph study. Certificate ranks are upper bounds, not
minimum mating distances.

Two checked legal extensions already illustrate the distinction. In the
unchanged [4,8] and [1,2] 5×5 rules, neither ordinary type alone can
ever mate, yet both together can reach actual four-actor checkmates from saved
natural full histories. The selected DRAW roots have cooperative mate paths
of ten and eight plies. These paths prove possibility and material interaction;
they are not forced wins from those roots or new Player fitness games.

## An executable boundary for the next segment

All four positive certificates join exactly to one [1,3] 5×5 AB/FLOOR
game, slot 15, AB as player 1 and FLOOR as player 0. At ply 39, AB captures
player 0's B, leaving K+A+B against K. The supplied root-40 certificate lifts
through this actual legal OR edge to a verified root-39 WIN for player 1,
without another search. The earlier five-actor ply-38 position is not resolved:
a new 90s/30k-per-target/depth-16 probe spends 60,000 nodes/16.335s and returns
UNKNOWN for both players. This is a new predecessor question, not extension of
the closed six-root proof cap. The capture is not established as an avoidable
error by the losing side.

A separate literal <=4-ply control on all six roots completes all 12 target
conditions in 26,466 visits. It sharpens the four successful winner bounds to
distances 4,3,1,2 at plies 40,41,43,42 respectively. The two unresolved roots
have no forced WIN within four; that is not a DRAW claim. This identifies
shallow tactical information on the proven suffix, leaving the earlier
material/depth decision as the useful open question. These posthoc diagnostic
roots must not become oracle-selected experiential training starts.

## Delivery and limits

The compact evidence capsule contains all episode records/receipts/models,
the finite support certificates, first-divergence argmax data, fresh observer
records/costs and the actual producer source strings as inert data. Large
natural graph caches and transient drivers remain ignored. One read-only
reader checks Core closure/Bellman ranks, full histories/PVs and TD arithmetic;
its receipt states which natural four-actor labels have only root/action
binding rather than independent WDL certification.

The main 2,199,061-byte capsule has SHA256
`96664fd4a0a0444bf147240f105e1908139b50212d200a36cbff88fd9a192a75`.
The sealed reader passes in 233.153s, checking 428,568 support vertices and
2,181,248 actual Core edges. An earlier reader reached all support cases but
failed on a sparse zero-count dictionary key; the reader default was fixed,
with the failure retained. No experimental result or budget was rerun.
The small loss-entry supplement carries the lifted certificate, predecessor
UNKNOWN receipts and finite short-win controls separately.
Its serialized certificate independently replays in 16 verifier nodes.
All 78 focused learner/Leaper/history compatibility tests pass. Confirmed
research intervals total 4,133.3501 seconds (68.889 minutes) before publication;
configuration, transport and publication administration are excluded. The
session keeps its original UUID and ends at a safe executable checkpoint.

[Evidence and reproduction](data/leaper_learning_support_20261023/README.md).

No old cap is resumed, UNKNOWN is not a draw, oracle labels do not train or
select starts, and no new worker/chat/Goal/timer or PRIMARY write occurs.
The next step must use the remaining cost/coverage question, not an unchanged
rerun or a claim that these prices are uniquely learned.
