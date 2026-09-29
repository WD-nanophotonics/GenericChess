# Frozen V2E failure: promotion option treated as a standing pawn premium

**Unknown.** Which general rule consequence is misrepresented by the failed
V2E static type-transition candidate, and can the existing frozen ledgers
isolate its effect without another coefficient sweep?

**Smallest direct observation.** Read the already frozen, post-reference
validation at `.generic_chess_flow/static-semantic-material-prior-v2e-human-validation.json`.
V2D and V2E use the same board capability `B0`; V2E adds type-transition
premium `T`. No candidate was recomputed, and no Xiangqi material value was
read.

| Chess quantity | V2D | V2E |
| --- | ---: | ---: |
| Raw pawn | 1.4923 | 3.1275 |
| Pawn transition premium `T(P)` | 0 | 1.6352 |
| N/P | 3.5460 | 1.6920 |
| B/P | 4.1876 | 1.9981 |
| R/P | 5.8108 | 2.7726 |
| Q/P | 9.9983 | 4.7707 |

The unchanged raw nonpawn values and added pawn `T` account algebraically
for the ratio collapse. V2E fails the predeclared Chess ratio bands; its
Shogi cosine is 0.9890 and pairwise ordering is 0.8974, below the frozen
0.9000 pairwise gate. This is a diagnosis of a failed historical hypothesis,
not a new selection of a formula by reference agreement. V2D also failed
its Chess gate, so dropping `T` alone is not a validated prior.

**Rule/model separation.** Chess rules permit a pawn to promote at specified
destinations; Shogi rules likewise distinguish promotion eligibility and
forced promotion. They do not make a far pawn's future promotion option
equally available in every board state. V2E's type-local `T(P)` turns a
conditional future transition into a standing value for all pawns. Its
probability and unit come from the declared source-conditioned event measure
and board capability score, not from a terminal payoff or empirical promotion
frequency. Treating this as a type-wide utility increment is the unsupported
step. A state-conditioned *immediate legal promotion* indicator is exactly
rule-observable, but neither its utility nor a static average over states is
yet derived. Later state-dependent analysis can use that distinction without
retroactively fitting V2E.

**Decision.** Do not repair V2E by adjusting a transition coefficient after
the failed gate. Keep its frozen failure and the Chess/Shogi controls intact.
V2D's Bishop/Pawn ratio remains high at 4.1876, outside its frozen band. The
prior exchange-survivability witness shows a real omitted reply consequence,
but cannot map it to a type-wide ratio without context weights. Any new
hypothesis needs its own independent argument, context rule, and small
falsifier before value validation. Xiangqi material values remain sealed.
