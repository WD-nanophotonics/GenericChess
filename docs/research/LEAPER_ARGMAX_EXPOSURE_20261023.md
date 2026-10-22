# Leaper argmax, natural exposure and actual learner cost — 2026-10-23 JST

Cheap geometry priors and modest search depth explain more of the observed
decisions than an immediate expansion of TD training would establish. This is
an exposed, bounded diagnostic result, not intrinsic piece prices, independent
holdout performance or a new product default. Science remains open.

## Shared infrastructure and division of work

The frozen new trajectories come from sandbox
`44d346484b8927309bf3437b99d4816a36fd3cf0`; the old five-actor controls use
`e8f4abf94bde7b6de1ab1a9acc3abfd24533c002`. Actual new diagnostic queries use
the shared infrastructure at `e3f7659864651d4e26c45472a876611bbe984103`.
Closing reuse is `06c7eb414b0ec8993f5d3d90606e8fcba36ff9d7`: leaper_design,
leaper_portrait, leaper_forecast and their tests are copied byte-for-byte.
Core/rules/session/ai have no branch difference. The closing suite passes
78 tests; earlier overlapping suites are not added to this number.

The closing helper fixes continuation from the actual initial_record and
qualifies only the played suffix. Measurements are not relabelled onto this
later commit. The zero-update episode below ran after that reuse. No PRIMARY
state, generator, forward campaign or default was changed. No worker, Agent,
Goal or schedule was created or modified.

## The old 17 residuals: parameter, tie and horizon are different questions

All 379 previously labelled five-actor histories receive literal full-history
D2/D4 argmax checks. At D4 both existing priors have 351 all-optimal supports,
22 mixed-WDL ties and 6 strictly suboptimal supports. Their actual lexical
choices make 17 errors: 11 mixed ties and 6 strict errors. Uniform randomization
over ideal argmax sets would add only 97/168 aggregate one-step WDL across the
379 histories. This is an observer calculation, not a randomized Player trial.

Fixed A=1 leaves are a+bB, with a,b in {-1,0,1}. Exact leaf-order intersections
are -2,-1,-1/2,0,1/2,1,2. Fifteen open-cell/boundary representatives therefore
cover the common numerical safety range -499999<B<499999 in real arithmetic;
terminal scores dominate there. This does not prove floating-point deployment
equivalence or cover a different normalization/evaluator.

The actual learner permits zero/negative B. Checking that domain repairs one
positive-only residual independently of ties, but four of the 17 remain strict
errors in every signed cell. No observed rule improves its best constant-price
uniform-argmax error count by adding nonpositive B. These are posthoc capacity
envelopes, not fitted weights or a proof that a context model is necessary.

The concrete repair is history 58b4a459..., ply7, root DRAW. At B=1, D4 strictly
prefers B d1-d3, whose exact WDL is LOSS; at negative B it strictly prefers
K d4-c3, which preserves DRAW. Negative price helps this context without making
B intrinsically undesirable. The deeper literal observer closes at 3,000,001
charged visits/228.814s with only four fully retained D6/D8 roots. Thirteen
remain unresolved; its counters include partial fifth-root work and are not
additional complete observations. No refill follows.

## New natural histories and their coverage limits

The 3,024 saved references contain 1,765 distinct complete GameRecords,
91,899 distinct-record visits, 86,058 full history roots and 43,952 Positions.
They are not 3,024 independent samples. PRIMARY's 96 invalid layout slots remain
outside the actual-game census and are not imputed.

| Observer | Actual time | Completed coverage | Retained limitation |
|---|---:|---|---|
| <=3 actors | 1201.777s | 51 complete rule closures; 57,872/64,428 histories | 1 partial rule, 6 unattempted; 6,556 missing labels |
| 4 actors | 1200.434s | 73 complete components; 2,169/14,139 histories | 1 partial, 222 unattempted components |

The four-actor prefix covers 16 fingerprints. Its config mistakenly described
round-robin ordering; the executed source actually sorts fingerprint/roster.
The error was identified while running and recorded without a restart or cap
reset. Results retain that lexicographic cost-selection limitation. Partial
four-actor labels/costs survive; that older executed driver did not persist its
unclosed graph. The maintained driver is corrected for future work; the exact
executed source is preserved.

Labels use the previously qualified plain-Leap/remove complete-graph and
count-three draw-sink/strict-rank/remaining-clock argument, not a general
Position-only GameState quotient. The closure table contains 60,041 complete
root/action rows and leaves 26,017 outside it. Its complement can contain
separate positive WIN certificates without complete action labels.

Of 626 true max-ply DRAW references, 531 enter a proven structural deadzone
before ending; deduplicated counts are 351/420. Another 147 references/101
records contain an unconverted mover-relative WIN. These sets can overlap.
First proven entry is only an upper bound when earlier material layers remain
unlabelled. 8,709 actual AB calls/5,600,184 nodes occurred after proven entry.
That is paid cost, not measured acceleration or a deployed recognizer.

The new four-actor rows have 925 WDL forks and 346 histories with an observed
inferior choice. A fork is not automatically a learnable material opportunity.
With only A remaining, B cannot affect future leaves; with only one ordinary
type, positive rescaling preserves ideal finite-depth action sets. Earlier TD
eligibility can still receive a later terminal signal.

## Actual public learner queries

Fresh-TT public mainline q0, equal capture ordering, A=1, 8192 nodes and
1.5s/query with 10% reserved for PV replay remain fixed. Mixed A/B roots use
seven positive cells; 902 single-type roots use B=1 only. This reduces the plan
from 30,366 to 19,542 calls without WDL-based root selection. Missing conditions
are not filled by assumed draws or inferred policy receipts.

One metadata bootstrap failure occurred before any Player call: an invalid
layout row lacked fingerprint. Source/config/failure survive; repair consumed
the original 900s window ending 19:08:15 UTC. The repaired batch completes all
19,542 calls at requested depth in 606.633s, paying 2,557,298 nodes.

| Policy on the same 2,169 known histories | D2 errors | D4 errors |
|---|---:|---:|
| Uniform material | 65 | 13 |
| Frozen mobility-ratio prior | 41 | 8 |
| Frozen Static-price-ratio prior | 41 | 8 |

Both priors use the learner's pure-material leaf, not PRIMARY's complete dynamic
Static Player. Each completes 4,338 new calls/516,282 nodes in about135s; none
matches an exact reusable grid weight. All4,338 paired actions, PVs, nodes,
features and WDL agree between the priors. This is not two independent successes.
D4 prior versus uniform improves5 histories, worsens1 and sums to +4 WDL;
the worse choice was already erroneous, so error counts alone conceal it.
The whole14,139-source conservative WDL difference bounds remain
[-23936/14139,23944/14139].

On the1,267 complete mixed-type contrasts, positive price changes affect WDL
at40 D2 histories but only11 D4 histories. At D4,5 can improve uniform and6
can worsen it;7 fail every tested positive served policy. Literal complete
argmax on the17 price-sensitive/residual histories finds mixed-WDL ties at
B=1 in all17. This does not cover the separate single-type error or justify
global random ties, a larger model or intrinsic prices.

Uniform D4 versus D2 improves53 WDL choices, worsens0, and removes52 errors:
one improvement remains suboptimal. Actual nodes rise53,631→458,897, about8.56x.

A separately frozen600s D6 probe uses ALL2,169 available roots in the same SHA
order at B=1. It records1,281 calls/1,884,386 nodes:1,238 full D6,40 usable D5,
1 usable D3,2 unknown calls and888 unattempted. No continuation is authorized.

| Full-D6-completion-conditioned common cohort | Histories | Errors | Nodes |
|---|---:|---:|---:|
| Reused uniform D2 |1238|35|29,892|
| Reused uniform D4 |1238|4|250,239|
| New uniform D6 |1238|2|1,717,406|
| Reused mobility D4 |1238|4|252,276|
| Reused Static-prior D4 |1238|4|252,276|

D6 adds2 WDL improvements at about6.86x D4 nodes on this cohort. Among365
histories preserving WIN under both depths, rank stalls fall104→83. These
completion-conditioned one-step effects are not matched actual costs, strength,
an Elo ladder, or an assertion about the888 unattempted histories.

## Literal controls, actual consumer and next action

All66 committed initial roots (10+40+16) receive literal OR/AND Core checks:
13 have shortest forced win1,12 have shortest forced win3,41 have no forced
win within3. The last category is not DRAW/LOSS. The three-ply group includes
7 of the40 breadth rules and4 of the16 proposal rules. Historical next_NOTRUN
labels refer to44d input status; PRIMARY has since closed that proposal at e3.
This annotation is exposed posthoc, not a pre-fitness prediction or rule filter.

35 selected full-history all-defense WIN certificates complete in1,578 nodes;
6 producer corruption controls are rejected.48 independent literal clock roots
use4,940 nodes. The exported reader additionally rejects a missing defender,
replays379 old and2,169 new full-root bindings, checks selected exact signed
and new argmax scores,35 WIN certificates, all66 short-root results,279 literal
PV edges and every compact query/cost join. It uses the shared Core, not an
independent rules engine or regeneration of the whole capped graph census.

The actual maintained play_episode consumer has up to5s/query and reserve0,
unlike the diagnostic caller. ONE zero-update cost probe selects the minimum
metadata hash among all58 ready frozen worlds, without oracle filtering.
It selects[5,30], draws by the actual rule after20 plies/20 calls, pays5,548
nodes/1.849s and leaves both models unchanged. Candidate B-PV gradients are
zero in this one episode; there was no TD learner/update. This is neither a
cost guarantee nor a statement about other episodes or earlier eligibility.

Next, use a separately frozen, label-blind small cohort of the original50
corner-layout rules, both roles, through that same consumer. Retain value/PV,
gradient/eligibility distinctions, true terminals/UNKNOWN and total cost before
choosing a minimal TD-versus-cheap-prior pilot. Do not select training starts by
oracle, repeat the sealed caps, duplicate PRIMARY screening or add a framework.

[Selected evidence and reproduction](data/leaper_argmax_exposure_20261023/README.md).
Closed effective work is5090.55473 seconds (84.843 minutes). Unconfirmed open
intervals and administrative import/publication are excluded; session origin
and UUID survive. End at a safe checkpoint, with research and hourly recurrence
still active for the next continuation.
