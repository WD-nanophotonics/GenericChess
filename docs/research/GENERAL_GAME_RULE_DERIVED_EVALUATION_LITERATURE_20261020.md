# Rule-derived evaluation in general game playing — 2026-10-20

## Question

Does prior general-game research imply a different current choice between
rule-conditioned piece prices, a generic search interface, or learned values?

## Primary-source findings

Pell's METAGAMER takes symmetric chess-like game rules, derives per-game
evaluation and relative piece values, then uses a generic search engine. The
open AAAI-94 paper describes fixed material advisors separately from dynamic
promotion-distance evaluation. It explicitly says the static promotion-value
advisor was unfinished and absent from the reported experiments; play instead
used a position-dependent promotion-distance advisor. It also reports a
known limitation: the static checkers pawn value is too low without promotion
value, despite the separate dynamic term. This is a useful warning against
reading a static piece table as the whole evaluator, not a numeric transfer
estimate. The paper's metagame tournament compared versions of METAGAMER with
different advisor weights on generated games, but the short report points to
Pell's dissertation for the underlying experiments and does not provide enough
detail here to compare its budget or outcomes with current matched-game routes:
<https://cdn.aaai.org/AAAI/1994/AAAI94-212.pdf>.

Pell's later journal abstract describes the same broad rule-derived approach
and claims useful values on known and newly generated games. The full journal
article remains unavailable in this read:
<https://onlinelibrary.wiley.com/doi/10.1111/j.1467-8640.1996.tb00258.x>.

Clune's AAAI paper builds heuristics from stable features in the game
description, modeling payoff, mobility/control and termination separately.
Its examples derive chess material ordering but select square-specific piece
features for Othello, where total piece count is not a useful heuristic. It
uses those rule-derived functions with iterative-deepening minimax. This is
evidence for conditional, game-structure-aware evaluation, not one universal
numeric piece table:
<https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf>.

Michulke and Schiffel derive admissible distance features from a fluent graph
constructed from game rules rather than board-coordinate patterns. Their
Fluxplayer integration compared the feature against the prior system across 19
games (about 100 matches each) with mixed results: the distance feature helped
some complicated games, while its extra evaluation cost hurt others. In
Breakthrough suicide, accurately minimizing distance toward the losing goal
made play worse because the feature encoded the wrong objective direction.
Grounding the rule formulas also timed out or exhausted memory on some complex
games. This is a candidate method for scoped rule-derived distance terms, not
evidence for transferable material ratios or a direct solution for semantic
auxiliary-state valuation: Michulke and Schiffel, “Distance Features for
General Game Playing Agents,” ICAART 2012, DOI
[10.5220/0003744001270136](https://www.scitepress.org/PublishedPapers/2012/37440/37440.pdf).

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
price change. The 2012 fluent-graph work makes rule-derived distance a possible
separate feature route, but its mixed outcomes, objective-direction failure and
rule-grounding cost argue for a measured, scoped prototype only after a concrete
current distance gap is identified. It does not change static-price candidates
or evaluator defaults. Clune uses GDL and its feature model. Pell's 1994 paper's
separation of static material and dynamic promotion terms matches the current
architecture: `RuleSetEvaluationProfile` carries static board/hand prices and
promotion gains, while `Evaluator` adds a position-dependent promotion bonus;
the existing AI-evaluation tests cover promotion-zone and forward-distance
bands. A bounded integration check compared evaluator promotion-zone squares with
Core-viable allowed destinations in 48 generated classic-like rules (6x6 and
8x8; 192 owner/type cases): all 9,776 allowed pairs had a mobile promotion
target and there were zero zone mismatches. Before the first correction, an
intentionally custom legacy ruleset with empty allowed masks still received a
geometry-based heuristic bonus; mask-backed zones remove that false bonus. A
separate valid custom legacy ruleset allowed promotion only at a non-geometric
interior destination: Core generated the legal promotion, but the old geometric
zone missed it and rewarded an unrelated terminal-rank square. After switching
to allowed-destination masks, a second custom case showed that a mask target can
still be structurally dead: P->G was allowed at a corner where G has no
empty-board move, so Core emitted only the unpromoted action while the evaluator
assigned +3. Zones now include only mask destinations with at least one
promotion target mobile at that square, matching Core's viability check; the
forward proximity band remains. The existing static-zone test also exposed two
forced dead targets in `build_promotion`; its expected set now follows the
traced Core `_promotion_variants` contract. Focused evaluator, semantic-profile,
Native inherited-promotion and legacy-promotion tests pass 68. The 48-rule
generated comparison remains unchanged. This is a bounded correctness repair, not a result about
price utility, explicit-semantic promotion coverage, or cross-rule transfer; see
the current mainline for decision implications. Pell's source supplies no basis
for an API, default weight, static-price or training change; the separate
custom-mask correction is driven by the reproduced legal-action/evaluator
mismatch. Do not treat this
literature as a new experimental result or permission to reopen closed panels.
