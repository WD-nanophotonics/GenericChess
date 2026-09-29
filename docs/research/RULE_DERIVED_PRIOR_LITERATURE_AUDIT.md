# Primary-source audit of earlier general-game material methods

## Bounded question

After the frozen first-action service candidate failed, is there an
established, independently justified way to turn rules into relative
piece values without human-value fitting or an undeclared context
distribution? Read primary methods, not their reported resemblance to
conventional Chess values as a recipe for a new candidate.

## Pell's METAGAMER

Pell's [1994 METAGAMER paper](https://cdn.aaai.org/AAAI/1994/AAAI94-212.pdf)
is a direct predecessor: it takes rules for symmetric chess-like games,
including Chess, Chinese Chess, and Shogi, and derives fixed material
advisors before playing. Its per-type terms include maximum/average
static mobility, maximum/average eventual mobility, capturable victim
types, and goal-related eradication/stalemate features. Eventual-square
access is discounted by the number of moves; Pell explicitly notes
that a bishop reaches fewer squares than a knight but reaches many
sooner. This agrees with our independently computed finite-deadline
crossing, without selecting a deadline or a utility for arrival.

The paper's material run gives the applicable advisors **equal unit
weight**. It explicitly calls general advisor-weight assignment open.
The planned static promotion advisor was not implemented in the reported
results; Pell says that omission undervalued pawns. Its Chess resemblance
to expert ordering is an empirical observation, not a derivation of the
equal weights or of a game-independent material utility. The source
does establish that fast rule-only structural valuation is possible
under declared heuristic assumptions; it does not resolve the
comparison/aggregation principle our mainline still needs.

## Clune's abstract-game evaluator

Clune's [2007 AAAI paper](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf)
models payoff, legal-move control, and termination in an abstract game.
It selects stable features from *randomly explored game states* and
uses regression on sampled states for control and termination. That is
a distinct, explicit search-state distribution and learned
aggregation, rather than a state-free static material derivation. Its
reported Chess control coefficients rank pieces plausibly, but the
paper does not claim that their ratios are universal material values.
It reports a two-hour Chess analysis, beyond our cheap construction
budget. Its useful lesson here is to name payoff, control, and
termination separately; mobility alone is not declared winning value.

## Decision

Neither primary method supplies a coefficient-free replacement for
the rejected first-action service scalar. Pell is the closer baseline
for rule-only Chess-like games, but adopting its equal weights or a
particular eventual-mobility discount merely because its Chess ordering
looks familiar would repeat the same ungrounded choice. Clune's
sampling and regression could be a later deployment-specific route if
the mainline adopts that additional modeling assumption, with its policy
and cost declared first. Do not treat either paper as a frozen candidate or
open Xiangqi human material values on their basis.
