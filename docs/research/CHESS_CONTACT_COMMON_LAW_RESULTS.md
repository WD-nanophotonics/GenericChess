# Chess contact counterpart: Q/R exact, B censored

2026-10-05. CHESS_CONTACT_COMMON_LAW_DESIGN.md precedes coordinate/path controls.
Uniform ordered distinct(s,d,b) on8x8 has249984 triples, without conditioning
on colour, reachability or a queried mode. Native B/R/Q clear-ray source-only
preparation is explicit; no strategic survival or official game-value claim.

| Mode | Exact distance1 | Exact distance2 | Exact distance3 | Proved zero | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| R | 53760 | 194432 | 1792 | 0 | 0 |
| Q | 87696 | 162048 | 240 | 0 | 0 |
| B | 33936 | unknown | unknown | at least127216 | 88832 excluded through1 |

R's rectangle formula is unchanged. Directed Bishop-aligned pairs number560,
with784 interior-blocker triples, so direct B mass is560*62-784=33936.
Opposite-colour2048 ordered pairs contribute126976 unreachable triples.
Same-colour trapped source corners add120; trapped target corners add120.
Those sets are disjoint for8x8 and exclude opposite-colour mass. Source/target
traps here are permanent: Chess B cannot promote to Horse or change colour.

Queen aligned ray pairs combine896 orthogonal and560 diagonal pairs, with
1792+784 interior blockers, giving direct87696. A blocked orthogonal Queen
pair needs3 exactly when axis distance L is odd and exceeds its perpendicular
reach r. Only L5 at the two central columns/rows and L7 at the six noncorner
columns/rows contribute:96+144=240. Even L has a two-diagonal midpoint detour;
L<=r has a mixed orthogonal/diagonal detour. Otherwise the Rook3 route suffices.
Nonaligned nondiagonal pairs retain R's unblocked2 route. No generic assertion
that a Queen always detours in2 is made.

Thus for a shared0<gamma<1:

    w_R=(53760*gamma+194432*gamma^2+1792*gamma^3)/249984,
    w_Q=(87696*gamma+162048*gamma^2+240*gamma^3)/249984,
    w_B in[33936*gamma,33936*gamma+88832*gamma^2]/249984.

The exact Q-R gap is gamma*(1-gamma)*(33936+1552*gamma)/249984>0.
R minus the B upper has strictly positive coefficients19824*gamma+
105600*gamma^2+1792*gamma^3. Consequently this scoped task certifies Q>R>B>0
throughout the whole open parameter interval, without selecting a discount.
No full P/N vector, natural-context calibration or human-price validation.

Four independent tests check Queen2 feasibility against coordinate candidates
on3..6 square boards, mass identities, endpoint trap disjointness and shared-
gamma gap identities. Compiled B/R/Q metadata has exactly its quiet/capture
ray patterns, path_clear, no guards/promotion/history/postconditions, and enemy
remove_from_game; own_anchor_safe is explicitly omitted and drops mask-disabled.
Global castling/EP/rights hooks and full histories remain outside this virtual
law. No engine transitions or official goal observations were used in counts.

Next prospective use: this incomplete constructor CAN cover every encountered
ordinary mode in a specially declared native R/B four-piece child table. That
is a scoped development test, not permission to fill other missing coefficients,
open Xiangqi holdout or rename the old exposed selector report as validation.
Freeze the new operator/population before new transitions/labels; retain full
choices, tie sensitivity and unknown source outcomes under unchanged caps.
