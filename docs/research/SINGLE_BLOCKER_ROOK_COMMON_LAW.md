# A source-balanced single-blocker Rook task law

2026-10-05. Analytical construction lead after the planned ordinary-source
reversal; no coefficient batch, new game/goal observations or human-value fit.
It extends the fixed-frame task to a COMPLETE common population for one mode.

For a rectangle of width w>=2,height h>=2, area A=wh, choose an ordered distinct
triple(source s, stationary ordinary enemy target d, passive own blocker b)
uniformly over A*(A-1)*(A-2). Both owners have mass1/2. All other squares empty.
Query native Rook source, preserving its origin and allowed current transition.
This is the same explicit virtual source-only preparation task, no safety,
opponent turns, history, declarations or official legality. The triple law is
fixed independent of queried type and outcomes and could be reused for other
qualified modes; it is not rule-unique or automatically deployment representative.

## Exact distances with one passive blocker

Aligned s/d have distance1 unless b is strictly between them, then distance3.
In the latter case no first orthogonal move can reach a second aligned capture
without the blocker, and a two-line detour on any other row/column gives3.
Optional Shogi R->TR promotion cannot reduce the blocked case to2: the first
move is still orthogonal; its successor is either in front of the blocker on
the old line, or on the perpendicular line through s. The target is at least
two squares from s along the blocked axis, so the extra one-square diagonal
capture cannot bridge that gap from a perpendicular first successor. Absorbing
capture does not need survival after the event.

Nonaligned s/d have distance2. Their two orthogonal elbow routes share only
the endpoints, so one distinct blocker cannot disable both. Distance1 is
impossible for native Rook even if capture can promote. This argument is about
the declared clear-ray grammar and Shogi's specific TR continuation, not arbitrary
Rook-like rule effects. In one-dimensional boards blocked cases are unreachable,
so the w/h>=2 restriction is substantive; never extend these counts silently.

The number of ordered aligned pairs is L=A*(w+h-2). Summing intermediate
squares across directed horizontal/vertical pairs gives
T3=A*((w-1)*(w-2)+(h-1)*(h-2))/3.
For example, each horizontal distance k has2*h*(w-k) directed pairs and k-1
interior blockers; the vertical sum is analogous. Therefore
T1=L*(A-2)-T3,
T2=(A*(A-1)-L)*(A-2),
and T1+T2+T3=A*(A-1)*(A-2), retaining every source/target/blocker placement.

On the9x9 Shogi board these counts are99360,409536,3024 out of511920.
Thus p1=46/237, p2=4/5,p3=7/1185 and the task mean is
(46/237)*gamma+(4/5)*gamma^2+(7/1185)*gamma^3.
This is one scoped analytical task statistic, not an admitted static R price.
No511920 context engine batch was performed. The earlier actual pair qualifies
specific compiled semantics, not every triple by sampling; the extension is
the explicitly stated geometry/transition proof above. Independent small-grid
count and path controls are in test_single_blocker_rook_law.py.

## Cost and transfer decision

An algebraic mean avoids materializing all triples, but similar formulas may
fail for asymmetric captures, blocked legs, screen counts, source/history guards,
promotion access and anonymous hands. A uniform triple law intentionally includes
virtual native dead-square placements for other modes unless a COMMON viable-
source restriction is declared beforehand. Do not separately discard a mode's
unsuccessful/unsupported rows or normalize each mode on favorable sources.
Unknown applicability gets unknown mass, not an unreachable claim.

Next qualify the compiled native R/TR contract beyond visited nodes by source
analysis or a prospective bounded audit, and develop a counterpart whose costs
can be compared under this SAME law. Independently motivated law/discount and
deployment precision remain needed; no full vector or holdout release occurs.
