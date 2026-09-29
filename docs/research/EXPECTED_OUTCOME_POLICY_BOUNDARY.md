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

## Optional-action monotonicity check

The earlier [pure-rule optional-action theorem](PURE_RULE_METAMORPHIC_MONOTONICITY.md)
gives a direct resource-value stress test. At one maximizing state,
suppose the only legal action ends in Draw. Add one *optional* action
ending in Loss while preserving the old action and all its
continuations. Exact minimax remains Draw: the chooser can ignore the
new action. Under uniform-random action choice, expected payoff changes
from `0` to `(0 + -1)/2 = -1/2`.

Thus random-play expected outcome violates this weak monotonicity under
pure option addition. If a material token's proposed value is meant to
represent the strategic benefit of having optional actions, the random
policy's average cannot be used directly as that benefit: it can assign
a negative increment to an option that can always be ignored. This
does not invalidate the paper's empirical heuristic claim, and real
Chess/Shogi piece additions usually change more than one isolated
option, so the tiny graph is a contract check, not a piece-value
estimate. It closes only the claim that uniform random continuation
is automatically a game-independent *resource utility* consistent
with pure-option monotonicity.
