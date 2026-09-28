# Shapley marginal valuation: bounded context diagnostic

**Unknown.** Can the Shapley value turn rule-derived terminal outcomes into a game-independent, type-local material scalar without selecting a context measure?

**Smallest observation.** Compute the two-resource Shapley allocation in two finite, legal-choice contexts. This is a mathematical diagnostic, not an estimate for Chess, Shogi, or Xiangqi. No material references or gameplay data enter it.

## Principle and object

For a fixed context `c`, let `N` be the set of resources being valued and `v_c(S)` the maximizing player's minimax terminal payoff when exactly the resources in subset `S` are available under a declared counterfactual. The Shapley allocation is the average marginal payoff over all orders in which resources could be added:

`phi_i(c) = sum_{S subset N\{i}} |S|!(|N|-|S|-1)!/|N|! * [v_c(S union {i}) - v_c(S)]`.

This allocation is game-name independent once `v_c` exists. It has a reason to be considered for interacting pieces: it distributes a coalition's outcome gain among the resources, including synergy. Its axioms and arithmetic fix the allocation **conditional on a characteristic function**. RuleSet transitions alone do not specify which resources form the coalition, how to remove one while preserving a comparable legal game, what context to evaluate, or how to combine contexts. Terminal W/D/L also supplies only a declared outcome scale, here `Loss=-1, Draw=0, Win=1`; this scale does not become a conventional pawn unit.

## Direct finite-game diagnostic

Take `N={A,B}` under one finite rule graph with a context flag `c` set before the maximizing player's turn. In either flag state the player has a fallback move to Draw. The same conditional rule opens a move to Win for resource A when `c=c_A`, and for resource B when `c=c_B`. Both flag states are admissible starts; the graph does not prescribe their frequency. Every old move and continuation remains available as resources are added, so this is a pure optional-action counterfactual. The minimizing player has no further choice; the minimax values are therefore exact.

| Context | `v(empty)` | `v({A})` | `v({B})` | `v({A,B})` | `phi_A` | `phi_B` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `c_A`: A opens Win | 0 | 1 | 0 | 1 | 1 | 0 |
| `c_B`: B opens Win | 0 | 0 | 1 | 1 | 0 | 1 |

For two resources, `phi_A = [(v(A)-v(empty)) + (v(A,B)-v(B))]/2`, and likewise for B. The table follows directly. Any weighted mean of these allocations gives `A=w, B=1-w`, where `w` is the chosen mass on `c_A`. The type ranking reverses as `w` crosses one half. Reachability and the shared W/D/L payoff do not fix `w`.

**Decision.** Shapley allocation can be an interpretable *context-specific* decomposition after a counterfactual and payoff are specified. It does not supply the missing context selection or static material unit. In actual chess-like positions, removing a piece can also open a line, alter check legality, remove promotion or drop rights, or change terminal status; the pure optional-action construction above avoids those complications and therefore gives the principle its strongest simple case. The failure of a unique aggregate already occurs there.

**Rejection condition for a scalar route.** A proposed rule-only, type-local Shapley prior must specify a game-independent, rule-invariant characteristic function and context measure before value validation. If two admissible contexts with the same rules yield reversed allocations and no independent rule principle fixes their relative mass, the claimed unique scalar is rejected. The table meets that condition for this route. It does not reject Shapley values for a specified state, nor an explicitly modeled distribution for another scientific question.

**Next bounded hypothesis.** Examine whether initial-state reachable contexts plus an explicit adversarial, rather than probabilistic, comparison can yield a useful interval or dominance certificate for material. State exactly which initial histories and counterfactuals are compared. A guaranteed interval may be wide; do not relabel it as a scalar if it is.
