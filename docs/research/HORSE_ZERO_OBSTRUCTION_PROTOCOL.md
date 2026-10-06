# Independent zero-mass lower certificate, not complement reachability

New analytic question after target-leg counterexample: how much unreachable
mass can be proved without any full distance census? Freeze these two disjoint
obstructions before arithmetic enumeration. No source BFS or new game/query.

1. A target at any rectangle corner has exactly two incoming Horse moves.
Their legs coincide at its inward diagonal neighbour. That own blocker kills
every capture entrance, so all88 eligible sources are unreachable:4*88=352.

2. A source with two outbound leg groups can have no first action. Target on
one leg kills that group; blocker on the other leg kills the remaining group.
If the remaining group has ONE destination, blocker on that destination also
kills it. A target at a destination alone does NOT block its capture, so it
must not be counted as an ordinary quiet hole here. Only the four2x2 corner
source neighbourhoods have two leg groups on9x10.16sources*2=32 leg/leg cases;
corner sources add2 singleton-destination cases each (8), adjacent boundary
sources add1 each (8):48. A valid Horse move cannot have a rectangle corner
as its leg, so these target-leg traps have no corner targets and are disjoint
from category1. Total independently certified zeros>=400.

Verify all508 coordinate outgoing edges and their inverses, leg-group class
counts and all48 explicit first-action-empty worlds. No full world/path/BFS.
Budget shared with the preceding3216 motif study: <=5000 total primitive
motif/edge terms and15sec cumulative; earlier1579 forward-node counter unchanged.
Report exact obstruction cardinality, not exact full unreachable unless a
separate complement reachability theorem exists. Agreement with saved compiled
zero400 does not prove that theorem or admit the full H distance distribution.

Refine moment upper by assigning these400 independent zeros actual0, instead
of optimistic m(3), while preserving tau1/2 disjointness and both frozen laws.
No human prices, parameter tuning, labels or Xiangqi holdout. Write-once raw.
