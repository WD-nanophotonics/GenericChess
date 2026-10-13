# Current Shogi q0 execution and scheduling bridge

Two exposed Shogi roots show both execution and scheduling costs. Native legality
plus the existing Native readonly availability callback does not eliminate the
Core-state cost gap. Optimized persistent Native completes deeper horizons on
these small budgets, but its TT, comparator, replay and search work differ from
the specialized minimal alpha-beta. This is not a matched algorithm speed ratio,
a strength claim or a reason to change engine/UI defaults.

Base is 1a8c612c9506e93a19a97826a3d7ea3c28a17ec0; current source hashes and all
conditions are in data/current_shogi_q0_bridge_20261013.json. No production code
or Native binary changed. The installed binary remains
a5352f67bf5a0ed2a337c7c2e35a1015b32402765aa0c6469acadbc4fd987b04.
Scientific drivers, failures and raw rows are hash-bound in the purpose archive;
raw Slack, accounts, host profiles/XML and binaries are excluded.

## Declared conditions

Reuse scripts/search_backend_comparison.py CoreBoard/ShogiBoard/Material and
minimal_ab/iterative_minimal, actual AlphaBetaPlayer and SemanticSearchEngine.
Roots are existing shogi-middle (eight played moves, all nine history witnesses)
and shogi-promotion (fresh snapshot with initial sentinel). Complete board/drop
actions, promotions, hands, actual ply and relevant history remain. Entering-king
declarations and the 500-ply extension boundary are explicitly outside this
finite assay, not removed from the generic project target.

The arbitrary material vector is K0 P100 L200 N300 S400 G500 B600 R700,
TP/TL/TN/TS500, TB800, TR900; same full vectors are explicitly bound in Native
board/hand type-ID order, scale1, no dynamic/spatial/learned evaluation. Q0/hard0,
check-only off, root tactical off. Public Core uses Native legality and optional
Native availability, require_full_pv=True, cold65536-entry TT. Native uses cold
1MiB TT, exact-root option, ordering cache disabled. Constructors/audit precede
budgets; returned public-action/PV validation remains in measured caller wall.

Minimal adapters have no TT and use USI lexical ordering. Their very large
10^12 node administrative ceiling never binds; public Core/Native have no node
cap. These are not equal-node comparisons. Main/q recursive visits, iterative
repeated visits, legal calls, completed children and Native loop counters retain
their actual definitions. Native kernel elapsed excludes packing and public PV
validation; caller wall includes both. Ordinary concurrent load is allowed and
these small costs are observations, not a noise-free CPU factor.

## Actual qualified decisions and equal-time results

48 predeclared cells completed: two roots, fixedD2/1s/4s, two reversed orders,
four actual backends. All roots restore and all returned PVs replay legally in
Core. All literal PV leaf values, converted to root perspective by parity, match
their reported scores in this finite data. This does not generalize selective
TT/PV guarantees. Two additional actual GameSession played-prefix calls match
the fixed public Core/Native full tuples and preserve the entire game record.

Independent specialized D1 searches of all47 legal root children give exact
D2 argmax: middle -200 with {8h2b,8h2b+}; promotion500 with {5c5b+}. Thus the
minimal versus optimized middle choice difference is a tie, not an error.
Core middle PV [8h2b+,3a2b] and Native [8h2b+,8b2b] also differ. All full rows,
not just scalar/move agreements, are preserved.

|Root|Budget|Minimal specialized|Minimal Core Native legality|Public Core|Persistent Native|Minimal Core Native legality+availability|
|---|---|---|---|---|---|---|
|shogi-middle|time1|4/4|3/3|3/3|4/4|3/3|
|shogi-middle|time4|4/4|3/3|4/4|4/4|3/3|
|shogi-promotion|time1|10/10|7/7|7/7|10/10|8/8|
|shogi-promotion|time4|11/11|9/9|8/8|11/11|9/9|

Depth cells list the two orders. At1s middle specialized/Native reachD4 and
CoreD3; at4s publicCore reachesD4 while both minimal Core configurations remainD3.
On promotion the availability bridge addsD7→D8 at1s but remainsD9 at4s.
Specialist/Native reachD10/D11, while publicCoreD7/D8. Deeper output is not proven
more useful play; moves/PVs differ by comparator and horizon. Native caller walls
exceed kernel budget by about5–12ms in these cells. Core commonly returns slightly
before the budget. Report actual wall, not exactly identical end-to-end deadlines.

## Same-algorithm work and execution attribution

Sixteen separately frozen trace calls compare the very same minimal algorithm,
terminal/material policy and comparator. Every corresponding entire visited
action/leaf stream, work count and scalar/move matches Core versus specialist,
including both orders. USI middleD3 uses10426 nodes; packed uses6079 and changes
canonical move 2h2d→8h2b+. PromotionD6 uses850 USI versus1087 packed and changes
5c5b→9i8i. Packing order reduces one tree and increases the other. The specialized
packed diagnostic converts state/actions through Core for ordering, so its cost
must not be used as a primitive speed ratio. Trace hashing also costs time.

Eight uninstrumented USI controls retain identical work. Middle Core legality-only
costs .96929/.93178s versus specialized .09489/.10614s; promotion .07458/.07736s
versus .00412/.00421s. The subsequent existing-availability supplement has eight
fixed controls plus eight1/4s calls. Its matched middle cost .79964/.79942s versus
.09457/.09402s (8.46/8.50 times); promotion .06123/.06032 versus .004073/.004093s
(15.03/14.74 times). Supplemental old/new settings are not contemporaneously
counterbalanced, so do not convert their difference into a clean percentage gain.
All fixed work/results agree, no operational Native fallback or availability decline.

The legality-only middleD3 profile has2.578s instrumented caller wall; push2.103
includes terminal1.139 and Python semantic has_legal_action .947. PublicCore's
availability option had not been supplied to this minimal bridge. One further
same-work profile after alignment gives1.994s; push1.511 includes terminal.555,
Native has_legal_action .368, component diff hash.252, full frontier.274 and
gave_check.161. Native state-only payload .1945/10894calls is nested inside
providers; do not add these cumulative numbers or call them all removable.
This identifies remaining state transport/history/check costs while keeping
actual correctness authority. It does not justify a new cache/kernel or skipping
Core commits. Existing frame-bound check reuse already exists; duplicating it
would not address the measured mandatory gave-check computation.

## Failures, verification and next choice

140 retained successful calls plus two search calls rejected/lost at private
recording boundaries were physically executed (142 total). One child query
restored its child root but the fixture expected its original parent; repair
snapshots the expected child SFEN/fullhistory. A callback's lazily initialized
metrics caused a serialization KeyError after a completed query; its result
was not invented. Saved first cell survives and only remaining declared cells
continue. A final summary missing declines key required zero-query postprocessing;
separate verification checks all16 actual rows. One PowerShell quoting repair
and its declaration guard made zero additional queries. Original producers and
failure notes remain in the archive. None was a production engine defect or
a user-action blocker.

41 existing relevant tests pass with zero failures/errors/skips. No new mirrored
test framework is introduced. Current production suite was not fully rerun for
this evidence-only delivery; prior2328 production result stays historical.

Next prefer one actual required Core transport/check primitive with a changed
premise and finite full-state/history control, or a specifically aligned canonical
reference if that can change the chosen API. Do not compose current persistent
Native/specialist speed parity from unequal algorithms/TT/PVs, extend old budgets
to find gains, or use this two-root q0 assay to claim Native q4 support.

## Begun next step: existing Core TT/PV contract

After the bridge closed, six separately declared cold fixedD8 promotion calls
compare full-PV+TT, short-PV+TT and full-PV withoutTT in opposite triples.
All six have the identical complete eight-move PV, action5c5b+, score500 and
11953 visits. Both TT arms have1437hits/zero bound cutoffs and take1.907–1.937s;
noTT haszero hits and takes1.281s in both orders. This finite same-work observation
identifies avoidable TT overhead in this sparse root, not a universal disable
policy. require_full_pv itself adds no work here. A zero tt_cutoffs counter alone
would not imply zero TT utility: EXACT TT early returns use a different branch.
Here unchanged complete output/work is the additional evidence.

The first checker omitted legal_actions import after its search completed;
preserve one unrecorded result and failed source, do not invent its tuple.
One attempted shell repair and its plan guard executed zero queries. Corrected
six cells are in the separate immutable tt-contract.zip and index
data/current_shogi_tt_contract_20261013.json; the first bridge archive stays intact.
Across this segment:146 retained successful,149 physical research calls, three
failed/unserialized boundary results. Existing41 interface tests cover production
source; no engine source or test definition changed. Next ask whether this
existing TT control transfers to the already measured played root at matching
fixed horizon before considering any consumer choice. Do not redo the q0 plane
or infer a global/default TT policy from the sparse position.
