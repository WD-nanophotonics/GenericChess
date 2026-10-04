# Finite-reference H2 path and closure results

2026-10-04. Frozen six-root diagnostic completed,2316 visited public/binding
choices,24 authoritative transitions,0.485s. Caps15s/5000 choices/24 transitions
and128/state respected. All sampled reward projections agree with independent
child enemy-board counts; history advances1 to5, resources remain accounted
for and ordered tag trace succeeds. No outcome labels or material vector.

Reference mu is one fixed feasibility-selected state/tag per refined mode,
NOT the original proposal population. Uniform complete-choice policy includes
all actors, promotion branches, drops and available claims. g_ref and the
actual-child r(z) are exact one-own-action expectations under that finite law;
the FIRST cycle is a single randomly selected own/opponent branch per root.

| Mode | g_ref | Actual child r(z) | r(z)-prediction |
| --- | ---: | ---: | ---: |
| Chess board/P/P |0|0|0|
| Chess board/P/Q |3/68|1/20|1/170|
| Chess board/Q/Q |1/12|1/13|-1/156|
| Shogi board/P/P |0|1/49|1/49|
| Shogi board/P/TP |1/54|1/54|0|
| Shogi hand/P |0|0|0|

The tag remains wholly in its original mode at the first-cycle endpoints;
no unsupported reference modes occur in these six branches. This does NOT
qualify absent Chess P/B,N,R references or generally mixed anonymous hand mass.
Every sampled first-own reward is0; the second sampled own action earns1 only
for Shogi P/P. The expectation comparison is more informative than those rare
0/1 path rewards. A surviving hand tag not chosen to drop still has g=0 here;
no hand premium or positive coverage follows.

## Statewise mismatch and a stronger one-root conclusion

For any constant c and same-mode states with exact expectations r1,r2,
max(|r1-c|,|r2-c|)>=|r1-r2|/2. Our inference: the root/child pair gives lower
bounds1/340 (Chess P/Q),1/312 (Chess Q/Q),1/98 (Shogi P/P) on a uniform
statewise error guarantee. These witnesses do not alone measure a general
population's signed average, usefulness or WDL calibration.

Shogi P/P permits a stronger finite-reference inference. The marked Pawn
starts(8,1); its only own first action is unpromoted forward(8,2). Other own
actions leave it idle; standard enemy actions either leave its owned mode
unchanged or capture it, absorbing ownership. No first-cycle surviving tag
can enter TP or own hand. Thus refreshed continuation always predicts0 for
this particular reference root, and true second service is nonnegative on
every branch. The observed legal branch is Pawn(8,1)->(8,2) among51 choices,
then enemy Gold(7,4)->(6,4) among40. Its exact child expectation is1/49;
positive branch probability gives e_P/P >=1/(51*40*49)=1/99960>0.
This bound assumes the qualified standard own-primary/enemy-victim action
contract; it is an analytical certificate from the complete frozen choice
table and actual branch, not complete enumeration of all first-cycle children.
It rejects exact mean closure for THIS point-reference law, not every richer
reference law, approximate tolerance or the whole lifetime construction.

Chess P/Q keeps3 tagged capture alternatives but full own choices change68
to60; Q/Q keeps4 while choices change48 to52. Some mismatch is action
competition/denominator dependence rather than a new intrinsic piece ability.
The complete-action policy is explicit and can be studied, but transfer to an
optimizing leaf selector still needs independent deployment evidence.

## Advisor reconciliation and next consequence

GC-SLACK-20261004-191008-926c1853, root1791108631.338719, reply1791108755.841079
was fully read/preserved, no further pages. Adopt conditional expectation at
the actual first-cycle child (already implemented independently), same-mode
error bound and origin-equivalence/policy controls. Dot checked committed
proposal and Li/Walsh/Littman; numerical results here are local Agent evidence.
Its response is theory advice, not independent execution or publication approval.

Dot correctly notes H2 reward occurs at first/third plies: fourth ply adds no
reward. Our four-ply run explicitly also qualifies second-cycle identity,
resource/history and endpoint trace; later pure H2 reward experiments should
omit that unnecessary final reply. No rerun merely to shorten this frozen run.
Origin aggregation needs either an explicit target mixture OR qualified rule
equivalence, not a universal mixture prerequisite. Native/P-origin Queen
contexts differ in background resources; inspect equivalence at matched current
states before interpreting their different reference means as static prices.
No full coefficient sampling is licensed by this diagnostic.
