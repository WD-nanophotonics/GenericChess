# CAUSAL_DIAGNOSTIC: held-token re-entry successor states

## Unknown and minimum observation

The unknown was whether the executable generic RuleSet path can identify
distinct legal board states reachable by dropping a token just transferred
from the opponent's board into the capturing owner's hand, separately from
the opponent-board removal itself. A paired one-capture static position and
Core's public legal-action/state-transition APIs are sufficient; no game or
search is needed.

## Observation

The V2A/V2D prior ledger records held/drop patterns and masks as excluded
semantics, not as a scored component or a state-conditioned set of legal
successors. The isolated diagnostic in
`scripts/diagnose_held_token_reentry.py` takes pre/post-capture positions,
matches an opponent base-token removal to a hand-count increase, temporarily
sets that owner to move for a static continuation probe, then uses
`legal_successors` and canonical position identity to collect distinct drop
successor states. It does not run a material formula or production evaluator.

Small executable semantic RuleSets confirmed:

- capture-to-hand and remove-from-game both remove the same opposing board
  token, but only capture-to-hand yields a re-entry candidate;
- no allowed destination yields an empty set; one and several distinct legal
  destinations yield correspondingly distinct states;
- the executable same-file pawn-drop restriction excludes forbidden squares;
- duplicate equivalent drop descriptions collapse to one canonical state;
- type-label renaming preserves normalized destination squares, and owner
  reflection preserves their reflected set.

This demonstrates a generic future-choice opportunity: a reusable held token
can re-enter the board into legal states. It does **not** show that the raw
number of destinations is material value, nor justify any coefficient or
normalization. The set is evidence about rule-derived option availability;
overlap, downstream consequences, reachability over time, and strategic
choice may make its cardinality a poor value proxy. Board-removal affordance
remains a separate observation and is not added to this set.

## Limits

The probe is static and one-ply. It resets the side to move to the capturing
owner without modeling an intervening opponent response, and generic hand
state identifies indistinguishable pieces by owner and base type, not
individual physical-token identity. Conditional rules that need history or
future state remain outside this observation. No human material references,
weights, score comparisons, games, Heavy work, Courier writes, or publication
were used.
