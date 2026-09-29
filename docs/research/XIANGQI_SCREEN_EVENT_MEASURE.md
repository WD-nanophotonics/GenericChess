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
yet combine source/target zones, blocker guards, own-anchor safety, or
a full Xiangqi action event measure. This is one semantic primitive
toward the cross-game prior, not a Xiangqi material score.

The next bounded guard check found that 24 of the 25 compiled exact
occupancy guards are owner-agnostic count-zero tests on a single
owner-relative horse-leg or elephant-eye square. The helper now maps
those to one `empty` cube and the test checks owner mirroring. The
remaining guard requires an opponent of explicit type `G` at the
target for `general_facing_capture`, an anchor-only action. A
three-label empty/own/enemy measure cannot express the opponent's type,
so the helper rejects it. This is a scoped unsupported semantic, not
permission to treat a generic typed guard as an ordinary enemy event.

The deterministic square-zone guard is also now evaluated from its
compiled zone and board shape. Tests cover the owner-mirrored General
palace and the Elephant's river boundary. Thus the local occupancy and
zone conditions needed by non-anchor Xiangqi movement are individually
representable. The following local event test composes one cannon
action; complete event coverage remains open. Dynamic own-anchor safety
remains excluded from this state-free prior, as in the frozen V2C model.

For one compiled cannon capture geometry from a central source, the
two-screen-square cube union conjoined with an enemy target has exact
V2C event probability `2426/85173`. The test independently reproduces
that fraction by averaging the hypergeometric expression
`P(enemy target) × P(exactly one occupied of two screen squares | enemy
target)` over the source-conditioned token-count distribution. This is
the declared maximum-entropy occupancy model's probability of an
intrinsic event, not a sampled position frequency or a legal-move rate
after own-anchor safety. It neither consults nor predicts Xiangqi piece
values.

The new local physical-event composer joins the compiled cannon path,
enemy target, and remove-from-game effect. It preserves source,
destination, target relation, and canonical removed square in its key,
and returns the same two disjoint occupancy cubes and exact probability.
The subsequent `INTRINSIC_BOARD_EVENT_COVERAGE.md` globally deduplicates
selected type-preserving board actions in all three RuleSets. Promotion,
held mode, and dynamic legal context remain outside this event ledger.
