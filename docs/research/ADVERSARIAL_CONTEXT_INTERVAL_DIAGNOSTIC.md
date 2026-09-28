# Reachable-context adversarial interval diagnostic

**Unknown.** Does restricting a piece-removal comparison to initial-state-reachable contexts make worst/best-case marginal bounds informative enough to support a static material prior or a type dominance certificate?

**Smallest direct observation.** Solve a finite zero-sum transition graph with two context flags and two resource flags. Every compared state is reachable from one declared initial node. There is no sampling measure, engine, human material value, or Xiangqi value inspection.

## Object and declared assumptions

For a fixed RuleSet, initial node `r`, full semantic state `s`, focal player, and declared removal map `R_t`, let `V(s)` be exact minimax terminal outcome. Include in `C_t` only paired states `(s,R_t(s))` for which **both** members are reachable from `r` and have the same context flag and player to move. With the *chosen* payoff coding `Loss=-1, Draw=0, Win=1`, define `delta_t(s)=V(s)-V(R_t(s))` and `I_t=[min_C_t delta_t,max_C_t delta_t]`. These are conditional bounds, not a material unit. For two types, pointwise dominance additionally needs a declared pairing of their comparison contexts.

The source of these assumptions matters. Initial-state reachability says which states may be compared; it gives no visit frequency. `R_t` is an intervention, not a move supplied by chess rules. The numerical spacing of W/D/L is a model choice; an ordinal statement can instead compare outcomes without subtraction.

## Finite witness

Let `r` have legal transitions to each state `(c,a,b)`, where `c` is either `c1` or `c2`, and `a,b` indicate whether resources A and B are present. A fixed legal terminal continuation from each state gives the focal player's outcome in the table. One can put the choices leading to these states under either player at `r`; reachability of all eight nodes is unaffected. The intervention `R_A(c,1,b)=(c,0,b)` and `R_B(c,a,1)=(c,a,0)` pairs states already in this one graph. Each paired state has the same player to move. This is a synthetic game, so the removal operation is explicitly part of the diagnostic rather than silently attributed to Chess or Shogi.

| Context | `a` | `b` | Terminal outcome | `delta_A` when `a=1` | `delta_B` when `b=1` |
| --- | ---: | ---: | --- | ---: | ---: |
| `c1` | 0 | 0 | Loss | — | — |
| `c1` | 0 | 1 | Loss | — | 0 |
| `c1` | 1 | 0 | Win | +2 | — |
| `c1` | 1 | 1 | Win | +2 | 0 |
| `c2` | 0 | 0 | Win | — | — |
| `c2` | 0 | 1 | Win | — | 0 |
| `c2` | 1 | 0 | Loss | -2 | — |
| `c2` | 1 | 1 | Loss | -2 | 0 |

Exact one-step minimax gives `I_A=[-2,2]` and `I_B=[0,0]`. The former is the full possible range of a difference under the chosen payoff coding. A has a decisive effect in either context, but its sign reverses. Neither A nor B pointwise dominates the other on the paired contexts. Selecting absolute effect, interval width, a worst endpoint, or a context weight to rank them would add a valuation objective beyond the rules. Thus even restricting **both** counterfactual states to the initial reachable set does not guarantee a useful type-level bound. This is an existence counterexample, not a claim that all practical intervals are vacuous.

## Source check and route

The 2026-09-28 Tokyo-day Chat advisory suggested this four-branch test and stressed that robust bounds require a chosen comparison domain and intervention. Its captured response named sources without usable URLs, so the following primary links were checked independently: [Iyengar, *Robust Dynamic Programming*](https://pubsonline.informs.org/doi/10.1287/moor.1040.0129) specifies conditional-measure ambiguity sets and a rectangularity condition; the [FIDE Laws of Chess](https://handbook.fide.com/chapter/E012023) define illegal positions by legal-move reachability; the [Japan Shogi Association rules](https://www.shogi.or.jp/match/taikyoku_rules/) include board, hands, and side to move in repetition identity. These sources motivate caution about applying the synthetic `R_t` to actual game states. They do not prove the arithmetic above, which follows from the displayed graph.

**Next decision-changing check.** Before any Chess tablebase or broader enumeration, specify one legal, generic piece-availability intervention that retains a comparable full semantic state in Chess and Shogi, or show on a smallest rule-semantic witness why no such intervention follows from their rules. If an intervention is an explicit approximation, state its cost. Preserve the ordinal/context-dependent result unless a nontrivial dominance certificate survives a predeclared comparison domain.
