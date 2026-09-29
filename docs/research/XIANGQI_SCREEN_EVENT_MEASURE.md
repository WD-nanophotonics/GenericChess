# Xiangqi cannon screen under the finite-population event measure

## Bounded question

Can the compiled Xiangqi `path_count_eq=1, owner_filter=any` cannon
condition be represented exactly by the existing V2C finite-population
occupancy measure, without inspecting Xiangqi material references or
simulating games? The smallest useful case is a two-square intermediate
path.

The compiled diagnostic RuleSet has a 9x10 board, 45 action patterns,
one `path_count_eq` pattern (`cannon_capture_one_screen`), 17 patterns
with square-zone guards, and 25 with exact occupancy state guards.
Six compiler-emitted legacy drop patterns have zero allowed drop squares
in both owner masks; they are not evidence of legal Xiangqi drops.
These are compiled-rule counts, not an evaluation result.

For a path of squares `a,b`, exactly one occupied screen is the disjoint
union `(a occupied, b empty) ∪ (a empty, b occupied)`, where occupied
means own or enemy. In an illustrative finite population of four
remaining squares with two empty, one own, and one enemy, its exact
probability is `2/3`. Zero-screen and two-screen events each have
probability `1/6`, and the three events partition the sample space.
These counts are a unit fixture, not the Xiangqi occupancy prior.

`scripts/intrinsic_occupancy_cubes.py` now emits disjoint exact cubes
for a path-count predicate with owner filter `any`; it rejects other
owner filters and a cube count above 256. The focused test obtains a
two-square path from the compiled cannon geometry and verifies the
fractions through the V2C exact finite-population union evaluator. It
also checks cube intersection with an enemy target: with two empty, one
own and two enemy tokens among five remaining squares, the joint
one-screen-and-enemy-target probability is exactly `4/15`. It does not
yet combine source/target zones, horse-leg or elephant-eye guards,
own-anchor safety, or a full Xiangqi action event measure. This is one
semantic primitive toward the cross-game prior, not a Xiangqi material
score.
