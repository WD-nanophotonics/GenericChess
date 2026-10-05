# Constructive Gold reachability, retaining unknown exact distances

Continuation of the admitted Gold board task,2026-10-05. Gold has all four
orthogonal unit displacements, under both owner reflections. A single blocker
cannot disconnect any source/target on the9x9 board. This supplies a uniform
lower for the423885 unclassified distance>=3 worlds, without full graph search.

If source and target differ in both coordinates, the two monotone L routes
through opposite rectangle corners have disjoint interiors. One blocker can
hit at most one, so choose the other, length Manhattan distance<=16. If they
share a row/file, take the straight unit route unless blocked; in that case
step to an adjacent parallel row/file, follow it, then step back. The blocker
is on the original segment and cannot obstruct the detour, whose length is
axis distance+2<=10. Thus every world has a compatible Gold path of<=16 actions.
Only the last step reaches the passive target; no earlier action removes a
background piece. Base/current tags persist. The qualified virtual grammar
allows these moves; royal safety and alternating opponents remain omitted.

This also applies to correctly marked TP/TL/TN/TS board modes, NOT their held
deployment or unpromoted native modes. It proves zero unreachable mass here
while exact remaining distances are still unknown. The old frozen Gold2 census
and interval code remain unchanged. A separate constructive lower adds
423885*m16/511920 to its prefix lower, preserving its distance>=3 upper.
For the mixture the increase is423885/(511920*153), about0.005411959;
for fixed-half it is423885/(511920*65536), about0.000012635. No point prior or
unknown normalization maximum is introduced.

The independent coordinate-property tests validate the explicit routes on
ALL distinct(source,target,blocker) worlds for3/4/5/9 boards, without BFS,
compiled event generation, engine transitions or utility labels. Route lengths
attain the stated geometric bound; tests verify every displacement for both
owner orientations, unique squares and blocker avoidance. The constructive
argument, not runtime census alone, establishes arbitrary-world compatibility.
