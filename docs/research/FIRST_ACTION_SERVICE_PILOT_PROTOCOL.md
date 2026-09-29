# Pre-reference first-action service pilot

Status: proposed structural prior, fixed here before computing new
Chess/Shogi values or opening Xiangqi human references. A failed gate
rejects this formula; it is not a parameter-fitting exercise.

## Use objective and modeling assumptions

Treat a material token as a resource for satisfying an independently
drawn request to access a board square. Its capability is the expected
number of distinct *physical first actions* from which that same token
could eventually reach the requested square by a finite path of
positive-intrinsic-probability RuleSet transitions. This measures route
redundancy and spatial flexibility. Such flexibility is potentially
useful for attack and defense, but it is not a payoff, survival
probability, real visitation rate, or theorem about winning utility.
Human material tables will test that proxy, not define it.

Declare owner uniform over two sides, board source uniform over all `A`
squares, and requested target uniform over all `A` squares. For a token
fixed on board at its source, draw the other physical tokens and coarse
empty/own/enemy occupancy exactly as the frozen V2C finite-population
model. These are maximum-entropy reference contexts, not inferred
strategic position frequencies. The prior is conditional on this use
model; RuleSet semantics alone do not uniquely choose it.

## Frozen board-mode quantity

For current type `t`, owner `o`, source `s`, let `E(o,t,s)` be the
deduplicated physical board-action events in
`intrinsic_action_events.py`. An event has a postaction current type
`r(e)`, destination `d(e)`, exact local occupancy probability `p(e)`
under the V2C source-conditioned measure, and a canonical physical
effect identity. Optional promotion choices are separate actions;
forced promotion has only its forced result. Let `Reach(o,r,d)` be the
set of board squares reachable from `(r,d)` in the directed graph of
positive-probability intrinsic board-action events, including `d`.
Future type transitions are allowed; a captured token's later transfer
to hand and adversarial replies are not graph edges. Define

`F_board(t) = (1 / (2 A^2)) Σ_o Σ_s Σ_{e in E(o,t,s)} p(e) |Reach(o,r(e),d(e))|`.

Capture-to-hand and remove-from-game are retained in event eligibility
and physical identity. They receive no separate removal bonus: this
pilot asks whether the moving token can serve a spatial request, so a
capture and an otherwise identical quiet action are not counted as two
services. This omission may cause the pilot to fail as a material proxy.
Do not add a bonus after seeing validation residuals.

## Held mode, normalization, and exclusions

For Shogi held base type `t`, condition one optional token on being in
hand. The other optional tokens independently have fair board/hand
status as in V2C; mandatory anchors remain on board. Given an owner,
sample occupied board squares uniformly without replacement. This
defines `p_hand_empty` for a target. For the frozen Standard Shogi
inventory this gives `p_hand_empty = 121/162`, independent of target;
the implementation must reconstruct that fraction from the inventory
rather than special-case it. The held-mode service quantity is

`F_hand(t) = (1 / (2 A)) Σ_o Σ_{d in allowed_drop(o,t)}
                p_hand_empty(o,t,d) |Reach(o,t,d)|`.

The hand source has no board square, hence only the requested target
contributes one factor `1/A`. Treat `F_board` and `F_hand` as different
mode values for the same physical type; do not silently average them.
Normalize both by the positive maximum `F_board` among ordinary
non-anchor base types in that RuleSet as a reporting gauge. This supplies no
utility unit and no scale against nonmaterial search terms.

Dynamic own-anchor safety, history-conditioned en passant, Shogi pawn
nifu/drop-mate conditions, and terminal adjudication remain explicit
exclusions from the coarse context measure. The existing semantic
RuleSets execute those constraints, but this pilot does not claim its
events are legal in every complete position. If a new unsupported
intrinsic primitive appears, stop the numerical audit and report it.

## Falsifiers and execution budget

First verify exact event union, promotion branches, owner mirroring,
zero-probability edges, and a toy graph where source-product and
first-action service differ. Reproduce one compiled Xiangqi cannon
event probability without inspecting Xiangqi human values. Bound each
game's exact audit to 60 seconds and 100,000 geometry candidates per
type; reaching a cap ends that computation and calls for an algorithmic
cost diagnosis, not an altered score. Runtime material evaluation must
then be a table lookup per token, with no graph traversal or occupancy
sum during search.

Freeze the numerical implementation and its input manifests before
opening the existing Chess human validation reference. Run its
pre-existing comparison gate unchanged, then Standard Shogi as a
control. If either fails, report the failure and the general rule
consequence missed; do not tune the event weights, context distribution,
reach definition, or promotion handling against the references. Only
after that locked evaluation may the unchanged formula inspect sealed
Xiangqi human values as the holdout. An R5 exact-W/D/L root can then
test search-use sensitivity under a declared search contract; it cannot
fit coefficients or establish population performance.
