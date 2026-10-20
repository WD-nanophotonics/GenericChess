# Rule-derived evaluation in general game playing — 2026-10-20

## Question

Does prior general-game research imply a different current choice between
rule-conditioned piece prices, a generic search interface, or learned values?

## Primary-source findings

Pell's METAGAMER is described as taking the rules of a symmetric chess-like
game, deriving a game-specific evaluation function and relative piece values,
then using a generic search engine. Its abstract says the rule-derived values
were useful on known and newly generated games. The publisher page exposes the
abstract and citation; the full article was not available in this read:
<https://onlinelibrary.wiley.com/doi/10.1111/j.1467-8640.1996.tb00258.x>.

Clune's AAAI paper builds heuristics from stable features in the game
description, modeling payoff, mobility/control and termination separately.
Its examples derive chess material ordering but select square-specific piece
features for Othello, where total piece count is not a useful heuristic. It
uses those rule-derived functions with iterative-deepening minimax. This is
evidence for conditional, game-structure-aware evaluation, not one universal
numeric piece table:
<https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf>.

Stephenson et al. evaluate twelve heuristic variants across 695 fully
observable, alternating Ludii games. They estimate each heuristic's usefulness
with depth-2 alpha-beta win rates against combinations of the other heuristics,
then predict those win rates from rule-description (ludeme) features. Their
leave-one-game-out Random Forest result reports 7.48 mean absolute error and
7.68 average selection regret, versus 10.07 and 16.62 for the mean-label
baseline. This is evidence that game descriptions can help select among
heuristic families. It is not a test of numeric piece-price ratios transferred
between chess-like rules, and its game set, shallow search, opponent pool and
win-rate labels do not match our generated-rule objective:
<https://ludii.games/publications/COG2021-1.pdf>.

## Mainline consequence

The sources support retaining rule-conditioned prices/features as candidates
inside a generic search path. The 2021 heuristic-prediction result strengthens
the case that rule descriptions may condition which evaluation family is
useful, but it does not establish numeric cross-rule transfer ratios for
GenericChess's complete generated domain or the causal value of any static
price change. The Clune work uses GDL and its feature model; Pell's full method
was not read. None changes current API/default/training choices or supplies a
new same-rule action/outcome witness. Do not treat this literature as a new
experimental result or permission to reopen closed panels.
