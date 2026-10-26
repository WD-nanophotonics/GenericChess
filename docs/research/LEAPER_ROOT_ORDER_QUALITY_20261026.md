# Pure-Leaper root ordering and a quality-population screen â€” 2026-10-26

Two research-only ordering policies failed to establish a material, consistent
whole-call improvement on this development population. Neither is selected for
product activation or game acceptance. A separate original-Player resource curve
checks whether actual games in this population distinguish a large budget
contrast. The frozen24-game resource screen is complete and independently replayed below.
Product search, defaults, UI and the independent AUX checkout are unchanged.

## Question and separation of claims

The opening autonomous review at sandbox120668d0 asked for falsifiable cross-rule
search/quality evidence instead of another geometry catalogue or H6 iteration.
This study uses twelve ordinary-Leap rules, two full histories per rule, and the
actual DEFAULT/PVS controller. No saved geometry inputs, old p49/p53 labels,
16-game Native-service proposal, H6 prototype or solver graph is resumed.
All work in this new chain, including both prototypes, input/reader failures,
resource-screen preparation and delivery, remains charged together.

[The primary PVS paper](https://www.ijcai.org/Proceedings/83-2/Papers/040.pdf)
explains why first-move ordering and re-search interact. It does not establish
that generic Leaper heuristics rank moves correctly or that additional depth
improves decisions. We use its algorithmic distinction, not its chess timings.
An attempted later iterative-deepening reference could not be fetched; no result
or parameter is attributed to that unavailable text.

The public Player defaults have PVS and staged picking OFF. Our explicitly
recorded experimental controller enables PVS, with DEFAULT dynamic evaluation,
ordinary Q4/hard8, root tactics ON, separate cold TT for each fixed-depth call,
and requested Native legality/availability/check services. Staged picking,
aspiration, rule-clock cap, ordered qsearch and stop-after-root-win stay OFF.
The requested and actual provider routes are distinct: exported legality
counters are retained; per-service availability/check counts are UNKNOWN here.

## Inputs, preparation failure and exposure

Six predefined ordinary-Leap families on5x5 and6x6 boards give12 fingerprints.
Each has a royal K, two A and one B per seat, remove captures, no drops or
promotion targets, repeat4 and a96-ply rule clock. Two deterministic hash-modulo
Core preludes of length2/3 give24 complete GameRecords,12 roots per seat.
All24 exact records/states independently replay; legal root sizes range2â€“17.
Hash modulo is a deterministic convenience, not exact uniform sampling or iid
worlds. Families and two prefixes of a rule are correlated. All data are exposed
development data from first use, never a class-wide or independent holdout.

The first pre-registration materializer called nonexistent `submit_action`.
All24 PREPARATION_FAILED records and original source remain. Corrected separate
v2 preparation uses the actual `GameSession.submit` contract and supplies the
full inputs whose hashes were frozen before any Player query. No failed frozen
Player slot was refilled. Later reader repairs address `movement_atoms` and the
difference between standalone research dataclass actions and GameRecord wire
`kind` actions. They change neither actual returns nor expected chess outcomes.

## A: reuse an existing root scan hint

The ordinary root scan already evaluates successors and retains its best action
for fallback. A research source copy moves that legal hint first only at a root
with no TT best action; a TT move keeps structural precedence. It adds no evaluator,
Core or TT calls. This is a concrete existing-information consumer, not a new
stage switch. Cold D1 can avoid PVS record-high re-searches if scan and leaf
values coincide, but checked leaves still extend qsearch and break that simple
static premise. Later iterations normally use the TT move.

All96 planned calls returned:24 roots x D1/D4 x2 arms. All48 complete same-depth
pairs agree on score and action; PVs replay and producer root-mutation checks pass.
At D1, PVS re-searches31â†’7, evaluation calls555â†’528, and total setup/constructor/
query row wall0.292894â†’0.231437s. At D4, evaluations30241â†’30214 and budget events
54691â†’54638, but wall10.323831â†’10.396665s. Every hint event is D1. These tiny,
unreplicated aggregate wall figures do not demonstrate a useful deeper-search
saving. **Stop this policy; no tuning, default change or games for it.**

## B: use previous complete root-child work after the TT move

A separate policy orders non-TT root actions by descending main+q work spent in
that child during the preceding complete iteration, with the original order for
ties. D1 is unchanged. Scout and full re-search work are both charged; partial
iterations are never promoted into the ordering table. No scores or WDL labels
are used. This could help search selection, or prioritize expensive refutations
that remain unhelpful at the next depth. It has no universal monotonicity premise.

Three rotated arms distinguish unmodified code, a record-only observer, and the
same observer plus work ordering. All144 calls returned at requested D4/D6.
All48 complete three-arm groups agree on score; all candidate actions agree
with the record-only arm. The48 original/record-only pairs also agree on action,
score, literal PV, main/q work, evaluation, TT and PVS counters. This supports
observational fidelity in these runs, not a claim of zero timing overhead.

| Complete depth | Record-only wall | Work-order wall | Main+q events | Evaluations |
|---|---:|---:|---:|---:|
| D4 |10.3495s|10.0579s|54691â†’53205|30241â†’29327|
| D6 |101.4671s|98.9458s|549790â†’532380|290844â†’279573|

The D6 aggregate wall reduction is about2.48%, but the median per-root ratio is
0.9978 and only12/24 roots are faster. Rule-equal weighting gives wall ratio
0.9953 and work ratio0.9908; one root increases work about7.4%. Two posthoc
opposite examples retain the actual per-depth/root-child work maps, without
selecting more trials or fitting thresholds. Independent checks verify96 complete
root-work conservation identities and192 TT-first descending-order events.
Budget events are not unique positions or equal-cost operations. **Stop further
work-order iteration and game escalation: the modest mixed result is insufficient.**

## C: actual original-Player resource contrast

The frozen screen uses one metadata-selected h2 full history per each of the12
rules, exchanging the2.0s and0.5s original-Player policies between seats. Players
have separate cold tables at game start and retain their own TT across moves.
Both policies request D64/500k-event/Q4hard8 ceilings. This is an explicit4x
resource curve, not equal-budget algorithm acceptance. Neither ordering prototype
participates, and more time is not assumed to be stronger. All rules and timing
criteria were frozen before the first game; no game or failed slot was refilled.

All24 games reach actual Core terminals:2checkmates,8repetitions,13max-ply draws
and1stalemate. Long-budget outcomes are2WIN/22DRAW/0LOSS,13points/24games. Both
wins occur in family4 on5x5 and6x6 boards, two fingerprints from ONE curated
movement family; they are not two independent family-level replications.

A0.5s call actually takes0.5620938s, beyond its frozen0.55s eligibility limit.
Its actual Core result stays in the all-game table; its game and incomplete
color pair are excluded from the timing-qualified paired endpoint. There are
23timing-eligible terminal games (long12.5points) and11complete eligible color
pairs (long12points/22games). No tolerance was relaxed. These few curated,
deterministic, correlated rule pairs support neither an iid Elo interval nor
class-wide strength claims. They show limited outcome discrimination, not a
sufficient broad quality acceptance panel. The two weak ordering candidates
remain **NO-GO for strength acceptance**, not selected for another game batch.

There are1931 actual game Player returns:965long and966short. Long uses
1902.778s choose wall/1899.688s processCPU and10,173,151budget events; short
479.616s/478.328s and2,631,090events. Trajectories and call counts differ, so these
are resource accounts, not same-position causal speedup measurements. The batch
uses2446.211s including setup, recording and validation, below its3000s cap.
Total new Player returns across both ordering studies and games are2171;
new solver calls are0. The old16-game Native-service proposal stays deferred.

Independent saved-data replay binds every raw-return byte hash, complete query
history prefix, actual move, resulting final GameRecord and literal Core terminal.
It replays9636game PV plies without running a Player. Missing, caller-truncated
and no-contest outcomes are not silently promoted to DRAW. Four negative controls
reject a dropped history, changed budget seat, altered captured score and a false
unfinished/terminal interpretation. Earliest common-history divergence is retained
for the observed decisive case, but is not a local action WDL certificate: both
future policy and private warm-TT contents differ. No outcome-selected follow-up
query or third-arm solver was run.

## Evidence and cost boundaries

[Lossless data and plans](data/leaper_root_order_quality_20261026/README.md)
retain every frozen input/source/return and known failure. JSON gzip payloads
preserve exact original bytes before presentation, including plan/source hashes.
The saved-data readers never execute source capsules or refill frozen slots.
Fixed-depth row wall includes setup, constructor, choose and result conversion,
but not subsequent PV replay/final row write; batch and whole-chain clocks remain
separate. A cold Player/TT is not a cold machine/process/Native-library guarantee.
Observer overhead and ordinary concurrent load limit small wall differences.

Existing original-D6 row timers measure6.905s evaluation,14.110s explicit legal
requests and1.640s ordering inside101.759s outer. Their default source boundaries
are distinct; inclusive qsearch/root-scan clocks cannot also be added. The observed
evaluation region is only6.8% and ordering1.6%;79.105s/77.7% stays unassigned.
Even a hypothetical zero-time same-work local replacement cannot remove more
than its observed region under unchanged other costs. This is not a universal
removable share or a cache benefit forecast. No guess turns the residual into
an identified Native/transition/history/TT consumer.

The next proposed question is a matched, overhead-controlled fixed-work cost
allocation on the original path, not another cache/kernel implementation.
It is PROPOSED_NOT_EXECUTED. Before any new run, related collection/preparation,
engineering, failure, validation and delivery costs must be attributed explicitly;
a new session does not reset them. Any expected related>=120minute experiment
still needs USER assessment. The current round forecast is105minutes, whole
cap115 from09:13:07.8UTC, including all three studies and their failures.
Final accepted research-ledger/whole-delivery receipts distinguish actual work
from administrative/transport/idle gaps; no credits derive from session uptime.

Two later autonomous reviews, c0118089c3cd85b3dfa2068928a6e84347969ca9 and
578cd42b0672181dafa4f0bdb8015be109bd4cdc, were preserved/read in full. Their
fixed published snapshots precede these unpublished results. Adopt the concrete
GO/NO-GO, full-history/whole-cost/quality distinctions and no-old-route directions;
neither their text nor Dot advice grants a>=120minute extension or a new AUX task.
No further phase was added after reading them. Current explicit user authority
for shorter bounded work remains; AUX files, state and computation were untouched.

Scientific acceptance records66.243effective minutes/1891actual intervals and7
relevant regression tests. Full delivery time is measured separately; no new
research credit is added for publishing, messages or the delayed reply check.

## Late consultation and budget-boundary clarification

The opening Dot reply arrived481.635s after sending, later than the single+5min
check, and was read in full at closing. Its controller/provenance/cost cautions
are adopted; its concrete PVS OFF/ON ablation is DEFERRED, not executed or
attributed as the cause of experiments completed before reading it.

Dot correctly identified contradictory live text at6565: an older Current Main
still described extending representation-sensitivity into a real-controller
experiment, while the leading review correction and NEXT_WORK selected cross-rule
strategy design. That paragraph is now explicitly superseded. This study does
not reverse declarations, test encoding fallback sensitivity, use old geometry
inputs/results/labels or complete its36failed frontiers. It tests existing root
information as search-order interventions and a new prospective resource-population
endpoint. All current preparation/source work/failures/threephases/delivery stay
in one105/115minute budget. The earlier geometry109.781whole/65.585effective
minutes and H6 costs are retained, not erased. General controller-source knowledge
is inherited background; its exact reusable fraction was not separately measured
and is UNKNOWN, not assigned invented zero minutes. The independent-boundary
judgment rests on the different intervention/inputs/endpoint, not on a new UUID.
Any actual continuation of the old encoding question must carry its old cost;
any expected related>=120minute future run still needs USER assessment.
