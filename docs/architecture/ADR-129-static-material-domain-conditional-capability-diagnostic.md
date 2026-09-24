# ADR-129: Static material domain-conditional capability diagnostic

- Status: approved zero-game diagnostic; no material formula change
- Baselines: frozen V2C event measure, frozen V2D `U+C`, frozen ADR-128 per-owner weak-domain graph

## Unknown and minimum observation

The unknown is whether V2D source-local capability is coupled to invariant movement-domain size, such that multiplying global `B0` by `D` fails to represent a precisely declared same-domain random-target experiment. The minimum observation is an exact owner/source decomposition of V2D successor-option and capture-affordance contributions, then grouping those contributions by ADR-128 weak components. No games, search, Heavy, human-reference values, score modification, or evaluator change is needed.

## Source-level reconstruction

For each type `t`, owner `o`, and board square `s`, retain the frozen V2A/V2C successor grouping and compute exact unnormalized source contributions `u(o,s)`. Retain V2D's physical removed-square identity and compute exact `c(o,s)` from its distinct capture-event ledger. Set `b(o,s)=u(o,s)+c(o,s)`. All squares remain in the denominator, including squares excluded by intrinsic source restrictions; such squares receive the exact zero contribution implied by the frozen semantics, never a replacement value.

Reconstruct:

`U(t) = (1/(2A)) * sum_o sum_s u(o,s)`

`C(t) = (1/(2A)) * sum_o sum_s c(o,s)`

`B0(t) = U(t)+C(t)`.

Any failure to reproduce the frozen exact baselines makes this diagnostic inconclusive; do not renormalize.

## Domain-conditioned decomposition

For each owner's ADR-128 weak component `j`, with square set `S(o,j)`, size `s(o,j)`, and `w(o,j)=s(o,j)/A`, report:

`Ubar(o,j)=sum_{s in S(o,j)}u(o,s)/s(o,j)`

`Cbar(o,j)=sum_{s in S(o,j)}c(o,s)/s(o,j)`

`Bbar(o,j)=Ubar(o,j)+Cbar(o,j)`.

Verify `B0(t)=(1/2)*sum_o sum_j w(o,j)*Bbar(o,j)` and the corresponding `U` and `C` identities. Include singleton components. Report the domain-size/capability association descriptively; undefined or zero correlation is not evidence of statistical independence.

## Declared random-target diagnostic

For terminal current types only (no outgoing executable type-changing transition in the frozen semantic ledger), define this mathematical experiment: sample owner uniformly; sample a source square uniformly from the board; evaluate frozen `b(o,s)`; independently sample a target square uniformly; retain `b(o,s)` only when source and target are in the same ADR-128 weak component. The exact expectation is:

`J=(1/2)*sum_o sum_j w(o,j)^2*Bbar(o,j)`.

This is a same-weak-domain random-target diagnostic, not directed reachability, actual game deployment probability, payoff, or material value.

Also report the algebraic factorization `FCT=(1/2)*sum_o B0_o*D_o`, where `B0_o=sum_j w(o,j)*Bbar(o,j)` and `D_o=sum_j w(o,j)^2`, with `FCT-J`, relative error when defined, and `R_joint=J/B0` when defined. Do not multiply separately owner-averaged values. None of these quantities changes a score or receives a human-value comparison in this order.

Transition-bearing types retain their same-type domains and outgoing-transition ledger, but receive no terminal-domain joint payoff, neutral deployment value, continuation value, or corrected material score. Drops/re-entry, history/auxiliary rules, and dynamic positional legality remain excluded and ledgered under the frozen V2C/V2D/ADR-128 boundaries.

## Classification

`FACTORABLE` means exact baseline reconstruction and complete domain binding, with zero exact `FCT-J` for every terminal type. `NONFACTORABLE` means complete reconstruction and at least one nonzero exact error. `INCONCLUSIVE` means incomplete semantic/source-domain coverage or failure to reproduce V2C/V2D. Either result is diagnostic only; any later material formula requires a new Chat work order and scientific justification.
