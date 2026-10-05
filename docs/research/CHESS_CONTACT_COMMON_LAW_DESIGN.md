# Chess-first contact counterpart under the same population

2026-10-05. Declare analytical counterpart before coordinate count/path controls.
Same uniform ordered distinct(s,d,b) law, now8x8:249984 triples, both owners
equally weighted. Current native board R/B/Q, target ordinary enemyP, blocker
passive ownP. Explicit virtual source-only preparation: no king safety, castling,
history, EP, opponents or official terminal claims. Standard compiled B/R/Q
quiet/capture movement and remove_from_game matter; no source promotion exists.
Source-origin effects are separately scoped by CHESS_MINOR_ROOK_ORIGIN_RESULTS.md.
No coefficient fit, game batch, goal labels or Xiangqi holdout.

R counts use the already proved rectangle formula on8x8. For B, opposite
square colours are permanently unreachable. Additional unreachable same-colour
contexts occur when s OR d is a corner and b its sole inward diagonal neighbor.
There are30 such targets/sources per corner. For8x8 the source-trap and target-
trap sets are disjoint: distinct corners have distinct inward neighbors. Keep
these failures rather than conditioning on same colour or reachable squares.
Exact direct B mass comes from directed diagonal-pair counts minus interior
blocker counts. Remaining native B mass is only excluded through1, not fitted.

Queen direct contacts are the disjoint R-orthogonal and B-diagonal pairs.
Any nonaligned and nondiagonal pair still has an unblocked two-action R route.
Only blocked orthogonally aligned pairs can take3 Queen actions: let L be the
axis separation and r the maximum perpendicular reach from their common row/
column. If L is even, two opposite diagonals meet at the midpoint offset L/2,
which fits on at least one side of an8x8 board and avoids the axis blocker.
If L<=r, an orthogonal/diagonal elbow at perpendicular offset L gives2.
If L is odd AND L>r, no two-step Queen detour exists: two diagonal legs returning
to the axis require even L, and a mixed orthogonal/diagonal route requires
perpendicular reach L. The Rook three-action detour still attains3.

Thus sum over odd L: four orientation/direction choices*(8-L)*number of rows/
columns with perpendicular reach<L*(L-1 interior blocker choices). On8x8 only
L5/7 can contribute. Board B/R/Q pattern source audit must retain every excluded
dynamic/compound form before claiming compatibility with compiled semantics.

Independent controls: compare diagonal/interior and Queen3 formulas against
small coordinate partitions, check all two-step Queen candidate intersections
for the central long odd-distance obstruction and neighbors, and verify exact
shared-gamma Q-R ordering plus R-versus-B interval ordering. These are geometric
mathematics, not actual public moves/strategic values. Do not run a full mode
constructor or select gamma from outcomes. Next scope a useful complete-child
operator whose encountered modes are covered by these partial intervals.
