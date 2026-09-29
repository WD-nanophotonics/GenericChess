# Uniform enemy-anchor target adds no new service objective

## Proposed shortcut

After reading Pell's goal-related advisors, one might replace the
first-action pilot's uniformly requested target square with a uniformly
placed enemy anchor and call the result goal-aware. Before any new
candidate run, test whether that changes the mathematical quantity.

For a board of area `A`, let `e` be a physical first action with
probability `p(e)`, and let `R(e)` be the set of squares reachable from
its resulting type and destination along the pilot's positive graph.
The pilot's board quantity for type `t` is

`F(t) = (1/(2 A^2)) Σ_owner Σ_source Σ_e p(e) |R(e)|`.

If an enemy anchor target `K` is sampled independently and uniformly
from all `A` squares, then for every event

`Pr[K in R(e) | e] = |R(e)| / A`.

Averaging that indicator over the same owner, source, and event measure
gives **exactly `F(t)`**. No new rule consequence, target value, or
reply condition has entered. The already-rejected Chess candidate and
the exact pilot/V2C decomposition therefore apply unchanged. A
different *legal* anchor-placement distribution would change the
measure, but selecting it is an additional context assumption. In
Xiangqi, palace restrictions make a uniformly legal anchor distribution
nonuniform over the whole board, yet the failed Chess gate still blocks
opening Xiangqi human values for this candidate.

Target contact is also weaker than the games' actual terminal goals:
check, legal replies, and mate depend on the surrounding state. A
future goal-linked prior needs an independently declared state/response
model and a loss related to terminal progress. Merely renaming a
uniform requested square as an enemy anchor is not that model.
