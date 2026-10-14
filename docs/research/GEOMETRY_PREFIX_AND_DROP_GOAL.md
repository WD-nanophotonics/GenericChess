# Static geometry allocation and an explicit drop goal

Delivered fixes reserve terminal utility bands and keep a completed winning root
child on a later abort.187 research searches and independent finite-goal proofs
bind the changes; default q/MDP and actual stop reasons remain unchanged.

Science remains open. This segment evaluates two concrete questions: whether
reusing immutable compiled geometry prefixes earns its memory and caller cost,
and whether delivered searches retain an independently established finite
winning goal when legal drop space grows. Product defaults, Core, Native, stop
handling and UI are unchanged. No auxiliary checkout or process was modified.

## Geometry: repeated work does not imply useful savings

The original Core q2 search at seed2026102017/18x18,1024 searched nodes makes
79,284 geometry-candidate calls over456 geometry/owner/source keys. It constructs
143,866 prefix entries versus1,246 across the observed unique values. Those
unique values have83,604 reachable Python bytes. The observer returns original
candidate tuples; all non-timing decision fields match the unobserved run.

Two private candidates preserve exact compiled order and path semantics:
a4096-entry pure immutable-path LRU, bypassing paths longer than32, and an eager
table of every compiled geometry/owner/source result. Neither caches positions,
checks, legality, evaluation or terminal results. Each measured search starts
with an empty/new cache and fresh player/TT; incremental preparation is charged.

|Board|Content-LRU mean caller ratio|Eager mean caller ratio|Eager traced retained bytes|
|---|---:|---:|---:|
|12|0.9896|0.9682|2,632,016|
|18|0.9911|0.9825|9,679,168|
|24|1.0035|0.9997|34,863,392|

Ratios compare two counterbalanced orders per arm at4096 searched nodes,
ordinaryq2/hard8, unchanged evaluator and Core. All18 searches match every
non-timing field, including actual runtime pushes/pops31,142/30,945/61,267
on12/18/24. Finite all-compiled-endpoint checks cover14,112/36,288/71,424
owner/source entries respectively. This is exposed development under ordinary
concurrent computer use, not an exclusive benchmark or strength measurement.

The initial whole reachable-table sizes were2.64/10.26/39.60MB. A subsequent
static-only tracemalloc/object-graph check distinguishes shared input objects:
additional retained Python allocations are approximately2.63/9.68/34.86MB.
Neither quantity is process RSS. This refinement does not rerun searches.

Decision: keep both candidates private. The small/mixed caller effect, including
no useful24-board gain, does not justify product cache/IR/lifecycle changes or
another expensive resource curve. High cache-hit counts alone are insufficient.

## Independent finite winning goal

The existing quiet-check/drop fixture in
`tests/product/test_qsearch_correctness.py` supplies a concrete mechanism.
Before any compared query, direct immutable Core proof enumerates all19 root
actions: four force a root-side terminal win within three halfmoves. The producer
uses300 transitions; it calls no compared search/evaluator to label actions.

For the branching comparison, horizontally reflect the fixture's four-file
local arrangement, keeping whiteK(3,0), blackK(1,0), whiteR(3,2), one whiteR in
hand, then extend board extents to4/12/18/24. This intentional mechanism family
is not an unseen game cohort. Full legal drop space grows; no artificial
action filtering, omitted defense or reduced state/history definition is used.

Four reference actions are frozen before comparisons: rook(3,2) to(1,2),
to(0,2), to(3,1), and dropR(0,2). All16 size/action cases independently force
the same rootH3 win, using926 producing transitions. A separate proof consumer
reconstructs legal actions, verifies complete defender sets and replays299
certificate transitions across those references and the original19 actions.
Producing search visits and compact-certificate replay counts are distinct.

Each root is an explicitly declared analysis position with a complete one-root
history/witness, rather than a fabricated played prefix. Promotion is absent in
this scoped K/R rule family; supported drops and all relevant history remain.
It does not represent the project's full generated rule domain.

## Delivery comparison and attribution

The frozen comparison uses ordinaryq0/q1/q2/q4, hardcheck8, main depth cap12,
same16/64 seconds including incremental player preparation, fresh players/TT
and two reversed policy orders. Common compiled rules/profile setup is outside
both arms. Actual returned actions receive the same rootH3 objective, with two
halfmoves remaining after their selected move. A different winning action passes;
matching a reference PV or a higher score/depth does not establish superiority.

The existing minimal_ab implementation is the completed thin algorithm control:
same complete Core runtime and exact evaluator at fixed mainD3/q0 versus supported
search's ordering/TT/iterative/root-scan stack. Different defined work is reported;
it is not claimed to be an identical algorithm or specialized backend.

Final results and source corrections follow. Exhausted proof budgets would remain unknown, not false.

## Collaboration and limits

PRIMARY owns these Core/cost/finite-goal studies and sandbox delivery. DEV_AUX
continues its separate price/leaf and transfer work on sidemission. The completed
primary consultation and AUX45 thread were read in full with no new supplement
at recovery; raw outputs were saved privately before reconcile. The recovery read initially had no fixed AUX45 report; its later fixed-file
review and the evidence limits are recorded below.
There was no duplicate auxiliary training/game batch, routine wake/ACK loop or
cross-checkout write. Ordinary concurrency is normal; own brief proof/memory
diagnostics can overlap the main curve and timing is interpreted accordingly.

The collaboration log records actual new coordination and adoption limits.
Published evidence excludes raw Slack/account/private records and receipts.

## Completed results and two generic search corrections

187 actual research searches are closed. The pre-repair64call curve achieves
rootH3 success14/16 each forq0/q1/q2 and10/16 forq4. At18/16 and24/64 q4 misses
the finite goal while the alternatives pass;24/16 allfail. Missing H3 is not a
game loss or proof that a slower win is impossible. These historical rows are
diagnosis, not a current-policy ranking after repair.

All108 known-family choices across curve/MDP/minimal/cheap controls reduce to14
actions. Independent proof uses1711 producing transitions; a separate consumer
replays1485 certificate transitions, checking complete necessary defenses, with
zero unknown. All16 matchedCore/evaluator fixedD3 minimal/supported choices pass;
all12 first-child/full-root-scan/static-D1 cheap choices fail H3. Mean minimal/
supported caller seconds are0.046/0.061,1.665/1.860,6.479/7.149,18.173/19.852.
Defined work/order/iterative/TT differ; this isolates algorithms, not backends.

ExistingMDP32calls:4/12/18 known roots completeD12 in0.18/2.89/9.33s with
180/1640/3560 cuts, baseline16s retainsD6/D3/D2. Both keep the same H3 objective.
At24 neither makes cuts or retains H3 before repair; four fresh generated roots
also make no cuts (one immediate rootwin). Depth/completion is not strength;
MDP default remains off. Actual inventory/promotion/dynamic bounds4162..267890
are below10M, not a maximum-of-visited-leaves claim.

First delivered fix: only production/reference search total static utility
saturates at existing MAX_STATIC_EVAL10M. Per-piece limits did not bound summed
inventory/dynamics. Actual accepted large dynamic weights give7,000,002,000
withoutMDP versus4,000,001,900 withit; an override1,000,000,020 versus1,000,000,010.
A false3-billion heuristic can even beat an actual terminal win. Initial11
regressions fail9/pass2 before and pass11 after; an extra realMDP/full-defense
goal regression passes. Raw evaluator/profile output stays raw. Saturation
deliberately merges oversized heuristic rankings; it is not unbounded-order
equivalence. Twelve ordinary scalar-step controls match every nontiming field;
small caller ratios are finite noise-limited controls, not speedup evidence.

Second fix: the observer finds an already completed H3-winning root child at
11.95s on18/q4 and5.44s on24/q2, then the old controller discards it when a later
sibling times out. Only a completed positive terminal-band improving bound is
now retained on abort; no incomplete child, heuristic or losing branch is promoted.
Eight counterbalanced same16s old/new calls recover4/4 paired H3 targets from0/4.
All still report time_limit and last complete uniform depth1, not completedD2.
result_source completed_root_win identifies its actual q policy; a partial PV
prefix is not a certificate. Four node/cancellation/normal-completion controls
fail2/pass2 before and pass4 after. Combined16 new regressions pass.

Source chronology is explicit: geometry and64call diagnosis load8efc5b3f;
scalar qualification/MDP use the bounded-source step; completed-root retention
has a third hash/snapshot. No old result is rewritten as a repaired run.
The scalar compatibility timing does not claim to benchmark every later change.

Late review: AUX45 fixeded113f9a was read in full and its Git blob plus13/256
and-1/128 arithmetic verified. Reported6464science/6480physical games,112143go
and512perft are not PRIMARY reruns. H24 failures and conditional NEW64 H48 signal
remain separate; unresolved is not draw,2vs2.4 is uncertain, B720 main gain0.
AUX46 complete new thread/reply is read: unpublished coupled prices/scales remain
reports; adopt fixednative versusleaf-scale scope and wholefamily simultaneous
uncertainty, without new games/engine redesign. No routine auxiliary wake.

Dot's fixed-source summed-utility objection changed the first repair; it did
not execute private evidence or review the later completed-root code. One
premature checkpoint after a failed prerequisite read is withdrawn/preserved,
then reverified only when data exists; exclude it from validated-stage credit.
See data/geometry_prefix_drop_20261014.json and its exact archive/member hashes.
Full tested publication and remote SHA are recorded after actual publisher success.


## Validation closure

The complete four-layer run passed2468 and failed one preexisting positional
compatibility fixture. It incorrectly removed today's final3fields rather than
stopping before provenance, after runtime fields had been appended. The named
historical boundary and stronger runtime-default assertions now pass; production
code was unchanged. Corrected provenance, both repairs and delivery tests pass30.
A direct retest's systemTemp WinError5 was resolved by project-owned basetemp;
no OS/security setting changed and no SAC cause is claimed. Original failures
remain private. The prescribed publisher rechecks the same relevant targets
before push; a containing commit's remote SHA is verified separately.

Actual session elapsed95.709minutes includes complete regression and these
observed corrections; the60-90minute target was exceeded, without idle padding,
clock reset or backdating. Structural research count12 includes one withdrawn
premature checkpoint;11 stages receive validated credit. Science remains open.

[Fixed auxiliary45 report](https://github.com/WD-nanophotonics/GenericChess/blob/ed113f9af378504a844da3d13c2813b19120c858/results/dev_aux/SEGMENT_20261014_45.md).
