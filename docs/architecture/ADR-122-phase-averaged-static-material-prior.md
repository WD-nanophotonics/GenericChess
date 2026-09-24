# ADR-122: Phase-averaged static material prior (V2A)

- Status: formula frozen before reading human-reference metrics
- Scope: isolated zero-game Western Chess board prior and Standard Shogi board retention audit
- Production evaluator: unchanged
- Base semantic construction: ADR-121 V2 distinct local action outcomes, with the corrected coverage boundary in this ADR

## Single question and observation

The one unknown is whether replacing V2's fixed two-thirds occupied-square density
with a ruleset-bounded phase-averaged density changes the intrinsic board prior
in the direction required to remove systematic ray-piece suppression. The direct
observation is a static zero-game Chess calculation with Standard Shogi as the
retention control. Full games, search, Arena, Heavy, self-play, learning, and
additional rulesets are unnecessary.

## Frozen density model

Let `A` be the number of board squares and `T0` the number of physical piece
tokens in the executable initial position, counting each board token once and
not counting rights, counters, or auxiliary state. First inspect every compiled
executable action/effect. The bound is admissible only if no action creates a
piece token: movement and promotion preserve one token; a capture either
transfers one token to hand or removes it from play; a drop must pair one
hand-token removal with one board placement; and auxiliary-state effects do not
alter inventory. Any unclassified creation-capable effect fails closed.

Set `rho_max = min(1, T0/A)` and treat `rho` as uniform on `[0,rho_max]`.
Conditional on `rho`, each non-source square independently has probabilities
`P(empty)=1-rho`, `P(own)=rho/2`, and `P(enemy)=rho/2`. This includes the zero-
occupancy endpoint as a reference distribution for phase uncertainty; it is
not a claimed distribution of real game positions and its bounds are not tuned
from human metrics.

Events sharing a density variable must be combined conditionally before
integration. For a distinct outcome represented by the union of supported
occupancy cubes, compute its conditional probability polynomial `p(rho)` under
the three label weights, then integrate exactly:

`Pr(outcome) = (1/rho_max) * integral[0,rho_max] p(rho) d rho`.

The zero-bound limit is the value at `rho=0`. As a check, for `k` distinct
clear path squares, one quiet endpoint has phase average
`[1-(1-rho_max)^(k+2)]/[rho_max*(k+2)]`; one enemy-capture endpoint has phase
average
`([1-(1-rho_max)^(k+1)]/(k+1) - [1-(1-rho_max)^(k+2)]/(k+2))/(2*rho_max)`.
The implementation uses exact rational polynomial arithmetic, not fitted
coefficients or numerical quadrature. It unions duplicate descriptions of the
same successor before applying the uniform source/owner average. Promotion
branches, forced promotion, source restrictions, and path semantics follow the
V2 rules. A source piece is conditioned to exist at its selected source square,
as in V2; source squares are uniformly enumerated rather than sampled from a
position distribution.

The V2 fixed-three-label calculation is reported alongside V2A using the same
semantic event and successor grouping, for a one-variable comparison. No human
reference, type name, or ruleset name affects candidate values.

## Coverage boundary

`INTRINSIC_BOARD_SEMANTICS` includes movement geometry, quiet/capture endpoint
relations, path/screen rules, exact source restrictions, restricted regions,
directionality, immediate promotion outcomes, and other state-free constraints
on the moving piece. Any unsupported intrinsic board predicate makes the board
result `INCONCLUSIVE`.

`DYNAMIC_POSITIONAL_LEGALITY` includes `own_anchor_safe`, check legality, and
other global predicates depending on unrelated pieces or anchor arrangement.
These remain counted in the ledger and do not change intrinsic board values.
Their ledger reason is exactly `global positional legality; excluded from
intrinsic piece-type material prior`; no fitted correction is assigned.

`HELD_OR_REENTRY_SEMANTICS` includes drops and their inventory, nifu, and
pawn-drop-mate restrictions. These remain ledgered and do not block this board-
only comparison; this does not resolve Shogi hand/drop value.

History/auxiliary actions without a rule-derived stationary state distribution
remain separately ledgered and outside the state-free intrinsic calculation.
The V2 and V2A score construction otherwise uses identical semantics and
classification boundaries.

## Frozen reporting and decision boundary

Before any human reference is read, the formula, assumptions, exact-integration
tests, inventory audit, implementation, and test files are frozen and their
SHA-256 values recorded. The report includes raw V2/V2A values and quiet,
capture, path, source-restriction, promotion, dynamic-legality, held/drop, and
reachability diagnostics. Human values are validation targets only; no
coefficient, density bound, or per-type value may be changed after comparison.

A V2A pass is only a Chess/Shogi board-prior milestone. It does not resolve
Shogi hand/drop value, complete Priority 1, or authorize Xiangqi. A gate failure
is reported as a general structural revision; unsupported intrinsic semantics
are reported as inconclusive. No production evaluator change is authorized.
