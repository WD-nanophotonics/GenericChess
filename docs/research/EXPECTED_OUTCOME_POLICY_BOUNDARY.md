# Random-play expected outcome is a declared comparison objective

Abramson and Korf's [1987 primary paper](https://cdn.aaai.org/AAAI/1987/AAAI87-016.pdf)
defines a nonterminal evaluator as expected terminal payoff under
random continuation by both players. Each player chooses among legal
actions at a node; a terminal path's probability is the product of the
reciprocals of its ancestors' branch counts. This is a scientifically
motivated, game-independent *sampling policy*. It is distinct from
uniform weighting of complete histories and from uniform weighting of
distinct positions, the two measures in
`CHESS_HISTORY_CONTEXT_MULTIPLICITY.md`. The paper reports finite-game
and sampled-game experiments, and notes that direct random completion
sampling was costly enough to motivate learned estimators. It does not
derive a cheap static chess-like material vector from rules alone.

## Smallest objective separation

Consider an exact two-ply zero-sum finite game with terminal payoffs
`Win=+1`, `Draw=0`, `Loss=-1` for the root player. The root chooses `A`
or `B`; the opponent then chooses among these legal terminal actions:

| Root action | Opponent's terminal options | Uniform-random continuation | Minimax value |
| --- | --- | ---: | ---: |
| `A` | Win, Win, Loss | `(+1+1-1)/3 = +1/3` | `-1` |
| `B` | Draw | `0` | `0` |

The expected-outcome objective prefers `A`; an adversarial opponent
chooses its Loss-to-root option and minimax prefers `B`. Three opponent
options on `A` are the smallest branch count that gives a strictly
positive expected payoff with one losing option under this declared
payoff coding. No position distribution, material coefficient, or
human reference is used in this analytic witness.

This does **not** refute expected outcome as a proxy for useful play;
the paper explicitly proposes it as a heuristic under its policy.
It does establish that the uniform-action policy and payoff coding
are consequential assumptions, not consequences of RuleSet legality
or terminal ordering. For this mainline, a successor would still need
a cheap way to project that state-level objective onto static *type*
coefficients, an explicit context selection/weighting, and a frozen
Chess/Shogi validation before opening the Xiangqi human-value holdout.
Do not equate exact random completion with cheap rule-only calculation.
