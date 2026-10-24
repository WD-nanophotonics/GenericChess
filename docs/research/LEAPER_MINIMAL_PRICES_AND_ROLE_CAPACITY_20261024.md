# Minimal prices, dynamic utility and role-coupled mating capacity

PRIMARY_SANDBOX, 2026-10-24. The eight prospective unfiltered starts prepared in
[the preceding segment](LEAPER_DEFAULT_CONVERSION_AND_FRESH_MU_20261024.md) now
have actual complete forward evidence. Static material replacement has zero
finite payoff effect in both dynamic conditions; enabling the dynamic bundle
raises wins from two to six. This is a finite exposed-rule result, not a claim
that prices are irrelevant. A separate adjacent-rule comparison and a scoped
static proof distinguish loss of mating opportunity from poor bounded play.

## Scope, registration and actual cost

The complete 5x5 RuleSet uses King8 anchors, one A3 (Wazir+Ferz) for P0 and one
B10 (Ferz+Knight) for P1, capture removal, H64, repetition4 and stalemate DRAW.
No promotion, drop, reserve or auxiliary mechanic is present in this prototype;
they remain part of the long-term generic target. Fingerprint:
`173bd8ad8bc61414547559bea1bd9196f9d03f8fb5f3e0f35673f14c5108df77`.
Eight complete fresh named histories were sampled before search/payoff, from17
physical proposals with nine initial-check exclusions. All eight were retained.
No truth label or successful-trajectory filter was used. Root tuples
(K0,A0,K1,B1), zero-based row-major, are
(11,6,22,1), (8,5,18,13), (4,20,24,22), (15,17,24,10),
(2,6,17,10), (22,1,10,24), (11,15,2,16), (10,13,20,14).

Each decision uses D64,8192 counted nodes+qnodes,3s, ordinaryQ0,
check-only FALSE/hard8. Actual services are Native legality ONLY; availability
and check are FALSE. Players are fresh per game, retain TT within a game and
never use disk cache. Equal per-decision limits do not imply equal actual work.

The first natural DEFAULT cost game mates in13plies/21.4232843s. UNIT costs
156.3036371s and reaches H64 DRAW; fixed-unit-order FULL costs20.0037866s and
mates13. UNIT and FULL pilots are reused byte-for-byte in the32-cell factorial;
only30 new formal games are executed. Natural DEFAULT is a distinct treatment
but matches FULL's complete trajectory, not an independent performance sample.
There are33 physical main games including the natural pilot,17 distinct literal
records among the32 formal cells, and no random-seed replication claim.

The formal batch takes1942.9007009s including its30 new game calls/setup,
qualification and reuse verification; it excludes module imports and earlier
paid pilot computations. Summed32 game-loop times2109.6471915s are another
quantity because they include the two earlier pilots. The original per-game
`seconds` starts AFTER compilation and Player/profile construction: it measures
search/game loop/incremental recording, not the whole Python process. Original
per-case setup/import/final serialization times are UNKNOWN, not zero. Forecasts
reserved preparation/qualification/analysis overhead; caps were never extended.
A controlled zero-query setup5s regression exposed missing setup timing. After
all producers closed, future recording was repaired, retaining exact OLD executed
source capsules and all original outputs. No fitness was rerun for metadata.

## Isolated leaf-price factorial

All four arms keep UNIT ordering and a UNIT defender. UNIT is unit material,
dynamics OFF; STATIC_FIXED uses generated DEFAULT material, dynamics OFF;
DYNAMIC_FIXED uses unit material plus the default dynamic bundle; FULL_FIXED
uses DEFAULT material plus that bundle. Generated DEFAULT A949/B1051/K0 is
separate from actual override profiles. Unit material is A=B1000/K0. All
registrations, actual metadata and chosen query controllers are checked.

| controller | wins | draws | game-loop seconds | nodes | plies |
|---|---:|---:|---:|---:|---:|
| UNIT |2|6|745.611136|2341537|316|
| STATIC_FIXED |2|6|735.128213|2340246|316|
| DYNAMIC_FIXED |6|2|311.975835|982236|149|
| FULL_FIXED |6|2|316.932008|978297|149|

On the finite equal-weight eight-root distribution, material effect OFF=0,
material effect ON=0, each dynamic effect=+0.5 and interaction=0. UNIT/STATIC
complete records match on all eight roots; DYNAMIC/FULL match on six, with two
different draw trajectories. No IID population significance, all-rule conclusion,
learner admission gate, Elo claim or default change follows. Full replay checks
930queries,5453PV plies,6642316nodes, qnodes0,2103083 Native successes and zero
fallback;6633358 runtime pushes/pops balance.

## Price exposure is distinct from a strict useful preference

All737 nonterminal selected PV leaves satisfy the exact scoped identity
`default_material = unit_material - 51*(A0present+B1present)`.
The observed quantity classes are A-only512, both144, neither81; no B-only
selected leaf occurred. This identity depends on this roster/ownership and is
not a fitted generic quantity rule. Dynamic decomposition independently checks
attack-union2, empty royal escape5 and check50 terms.

A complete static functional census has28800 labelled placements,28200 distinct
physical boards (bare-K controls are repeated), not admitted/reachable histories.
A-only present/absent dynamic ranges are[-34,114]/[-35,35], giving a strict
sufficient material band threshold69. B-only ranges[-106,29]/[-35,35] give64.
Both actual weights preserve every weak leaf order after either capture. Min/max
on the IDENTICAL fixed complete tree then preserves argmax. Timed TT searches
need not build that same tree; no policy-equivalence theorem is claimed.

Pooled exposed leaves have92 quantity/dynamic classes. Of4186 class pairs,
static replacement splits255 unit ties; with dynamics,76 pairs strictly reverse
and three split unit ties. These may be different roots/histories/controllers,
not actions available at one root. The public reader reproduces these counts.
Thus real functional sensitivity exists despite zero observed price payoff.

The first actual price-dependent choice with dynamics ON is root1/query4,
P0 acting from a complete shared four-ply history. Four fresh cold D6 calls all
complete D6/main_iteration and still select different DYNAMIC/FULL actions.
Eight additional cold remaining-D5 calls evaluate those two candidate actions:
UNIT[0,0], STATIC[-102,-102], DYNAMIC[-7,-7], FULL[-108,-108]. Both candidates
TIE under every evaluator. Twelve new queries/64PV plies qualify. Other root
actions were not independently valued. This supports an iteration/tie-selection
explanation, not a strict argmax crossing or realized utility conclusion.
`completed_root_win` may legally retain a completed winning child from an aborted
higher iteration while `completed_depth` stays the last uniform iteration;
source review resolved that contract without changing engine expectations.

## Opponent movement can destroy an attacker's static mating capacity

Deleting A's diagonal orbit gives A1 (Wazir); B remains10. A static geometric
filter examines all13800 distinct K0/A1/K1 triples.10488 have nonadjacent kings;
1428 have A checking K1.1396 have at least two unblocked royal escapes, which
one B cannot block;16 singleton escapes are occupied by the capturable checker.
Only16 four-actor cages remain. All31 B masks and all16 cages are retained:
496 cases,240 safe Core defense frontiers,256 excluded previous-mover checks.

Exactly11 B masks permit static mate:
1,4,5,8,9,16,17,20,21,24,25. The other20 do not. In this finite vocabulary/5x5
roster this equals: B lacks Ferz AND does not contain BOTH Dabbaba and Knight.
Across75 single-orbit edges there are19 capacity losses; maximal positives21/25,
minimal negatives2/12. Ferz permits capture of the checking Wazir; Dabbaba+Knight
together attack both possible supporting-K0 placements. Extra B moves add
defenses or reject previously safe cages. This is not an all-board/effects law.

The actual A1/B10 target's separate full RuleSet qualifies all eight safe cages
and1428 bare-A checked frontiers/5456 defenses. Together with remove-only roster
exhaustion, P0 cannot checkmate along a valid continuation. This does NOT prove
minimax DRAW or avoidance of P1 losses. Static carrier layouts had no named
setups; their capacity claim was separately transferred by exact rule comparison,
not by pretending those carrier starts belong to the original eight-root law.

A common fresh witness uses K0b3,A0a3,K1a1,B1b1. The same A move a3-a2 mates
against B8 Knight, but against B10 Ferz+Knight there is exactly one defense:
B b1 captures A a2. Full initial/child/defense records replay. A1 and B8 each
lack singleton bare-K mating capacity, yet the joint roster permits mate through
an opposing blocker. Individual capacity labels do not compose into roster
impossibility. Context dependence alone does not refute constant average prices
under an explicitly declared distribution.

Observed setup/action-shape failures are preserved privately: changing B inside
old named setups caused INITIAL_ANCHOR_ATTACKED before any query; a safe common
static carrier fixes that scope. Core BoardMove has from/to, not actor_type_id;
resolve the actor from the original board. No expectation was patched to match
a failed output; failed originals remain distinct from repaired computation.

## Adjacent-rule actual forward comparison

A1/B10 fingerprint is711ca14035cb82e57ab82e658155437027c87a603a21cbd1f9a938c5910b57c1.
All eight physical starts remain, no admission/payoff filter. Fixed UNIT material
and ordering avoid the changed generated DEFAULT A678/B1322.16/16finishDRAW,
zero missing: each controller has6H64/2repetition. UNIT432queries/3000385nodes/
1113.212801game-loop seconds; DYNAMIC507queries/3497595nodes/1294.996229s.
All939queries/5860PV plies qualify. All16literal complete records are distinct.

The finite paired geometry effect is-0.25 under UNIT and-0.75 under dynamics;
dynamic effect changes+0.5to0, interaction-0.5. The static no-P0-checkmate fact
explains a lost terminal opportunity; these actual DRAWs do not prove rootWDL0.
First captures split8lostB/8lostA. Equal decision limits did not equalize work.
The actual cost pilot163.466876s is reused once,15new games; its paid loop was
subtracted from the original2700s total, leaving2536.5331241s frozen batch cap.
Actual new batch2253.6750507s, no extension/refill. Setup/import times of old
cases remain UNKNOWN. All49new physical games (33main+16adjacent) plus12cold
queries total1894Player queries, with11439game/coldPV plies qualified.

The wider panel had already been registered/executed before the latest direction
review adopted the smaller-diagnostic priority. Results/costs are retained, not
retroactively presented as executing that newer advice. No further price panel
is selected; current PRIMARY Main is the structural counterfactual work.

## Next step actually begun, not searched

A1/B8 retains all eight physical starts and complete new rule-specific histories,
fingerprint `b2f7417f518aab4ea1fbe7de999a91f036f4587af6c151d19ebe59567d466fd6`.
Both singleton remnants are exhaustively checked: A1428 checked frontiers/5456
defenses; B1600/7488. After any ordinary capture neither player can later
checkmate a bare king under this remove-only rule. A full four-actor fresh mate
witness nevertheless exists. Root WDL/reachability from the original eight starts
remain UNKNOWN. Preparation and3028 frontier checks use zero Player queries and
zero learner updates. This remains a conditional prepared reserve under the current structural Main.
No further caller-cost run is automatically scheduled. Reuse matching evidence
and preserve censor/UNKNOWN if a later specific question justifies execution.
No original dead-capacity sampler filter, nonzero utility gate, AUX solver,
learner activation or blanket deeper search is selected.

## Collaboration, authority and delivery

One original probe saved exact channel and full relevant threads before review.
Claude1792803069's first-action/dynamic separation was already executed in the
preceding segment; it was not rerun. The cold-policy Markov proposal is deferred:
fresh TT changes policy, and any exact closure needs full histories and its own
cost. An unpaired Fisher calculation on three paired streams is not our primary
inference. AUX fixed report e71968ff8ec5e3ab57cade9b965e44a23558780a is read and
attributed: learning exposure/rank/deeper targeted diagnostics remain AUX-owned;
PRIMARY did not rerun them or copy unpublished work.

The user's fresh direct permission allows the previously prepared3073-character
report and reaffirms ongoing bounded two-way exchange. That queued old report was
sent ONCE and exact parent payload verified at Slack1792808252.870899, referencing
56560fb3e24102792f72a005c5c5bdb52526943f. The later complete thread read found Chat1792808411; normal reconciliation now
marks the old request COMPLETED. Delivery, reading, adoption and execution are
separate: the new smaller-diagnostic priority was adopted after these frozen runs. New reports follow reviewed
push/full SHA and one merged message per existing probe, with no live wait/Dot.

Current direction now prioritizes [structural counterfactuals](LEAPER_STRUCTURAL_COUNTERFACTUAL_20261024.md).
The A1/B8 cost proposal is deferred; static opportunity and sampled outcomes are
not learner/truth admission gates. Material/dynamic results above are retained
secondary mechanism evidence, not a replacement for the structural Main.

Technical evidence: [manifest](data/leaper_minimal_prices_and_role_capacity_20261024/manifest.json)
and compressed exact UTF8 packet alongside it. Reader:
`python -m scripts.leaper_minimal_factorial_packet --packet <packet.json.gz> --manifest <manifest.json> --output <NEW.json>`.
It decodes data, binds sources and replays shared Core; it never executes capsules
or reruns search. This is a reproducible finite semantic check, not an independent
engine, full WDL, unseen-rule generalization or measured training improvement.
