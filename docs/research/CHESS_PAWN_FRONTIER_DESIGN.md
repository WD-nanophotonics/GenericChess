# Pawn rank-stratified support and two-action frontier: prospective question

2026-10-05, before new counts. Same native Chess249984-triple law, owner0
forward +y and owner1 by reflection. Initial EP absent, no opponents, stationary
own blocker and designated enemy target, compatible intrinsic source moves.
Existing g1/2 and density2(1-g) hypotheses remain fixed; no labels or tuning.

First derive the memo rank-stratified single-quiet-to-Q lower bound: on each
source rank with k remaining quiet actions, off-file target/blocker stratum
has24640 worlds, including770 direct captures. Use exact direct overlap once
and non-direct23870 at distance<=k+3. This does not require full promoted graph.

Then ask whether native Pawn's upper can be tightened by exact no-promotion
reachability/first-two-action geometry. A forward same-file own blocker at
distance j prevents promotion; the only possible contact is an adjacent-file
target at forward rank offset1..j. Exclude old forward-same-file zero worlds
before counting extra zeros. Double moves require both intermediate/destination
clear and cannot jump either physical token. Source on last rank cannot move.

Two-action routes: single quiet then diagonal capture; initial double then
diagonal capture; or single quiet PROMOTION then one promoted capture. Preserve
ALL Q/R/B/N promotion choices: Queen does not dominate Knight's capture squares.
For the promotion route count union(Q rays,N jumps), excluding direct P worlds,
old source and physical blockers along the new ray. Old source VACATES. No
post-hoc target filter or midpoint. Unknown other worlds stay>=3, not zero.

Derive formulas first, verify independently using explicit first-step geometry
and small/eight-board blocker worlds. No engine/goal/source observations, full
Pawn graph or claims auxiliary effects are modeled. Lower witnesses use single
quiet moves; two-action double eligibility treats emitted tokens as real but
no opponent move supplies an EP victim. One arithmetic check bounded15sec.
If upper and B lower separate under the two predeclared hypotheses, qualify
only their task ordering, not an intrinsic scalar value or independent use pass.
