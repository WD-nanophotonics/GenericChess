# Shallow initial Chess histories cannot identify all material coefficients

**Unknown.** Could a cheap sample of legal histories from the uniquely
declared Chess initial state supply enough inventory variation to
project a state-level objective, such as random-play expected outcome,
onto five static material coefficients? This checks *feature support*
before any outcome simulation or regression.

`scripts/audit_chess_shallow_inventory_rank.py` exhaustively enumerates
public RuleSet successors through three plies. It counts the White-minus-
Black board inventory vector `(P,N,B,R,Q)` at each depth. The limits are
10,000 generated histories per frontier and 30 seconds; exceeding either
aborts the audit. The initial run completed within 15 seconds locally.

| Ply depth | Legal histories | Balance vectors |
| ---: | ---: | --- |
| 0 | 1 | all zero |
| 1 | 20 | all zero |
| 2 | 400 | all zero |
| 3 | 8,902 | 8,868 zero; 30 `P=+1`; 4 `N=+1` |

Across **every** history through depth three, the bishop, rook, and
queen balance columns are identically zero. No weighting of these
histories, terminal labels, or regression loss can identify separate
coefficients for those types from a material-balance-only design.
Even Pawn and Knight variation occurs in only 34 of 8,902 depth-three
histories. This is a support/identifiability result, not a claim about
their strategic values or about deeper game states. It does not
justify increasing the horizon until all types appear: a deeper
frontier adds cost and still needs a principled context measure.
No human material reference, Xiangqi holdout value, or proposed
coefficient was inspected.
