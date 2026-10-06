# Promotion development control: independent source tie-risk evidence

Prespecified root White Kc3/Pb7 versus Black Kh8 yields all12 choices: eight
King moves and four promotions. Scores/full choice sets saved before probing
all12 author children. Both frozen contact laws uniquely choose b7b8q; unit
ties every choice. Source no-50-move Gaviota labels assign root utility1 to
Queen/Rook promotion and all King moves,0 to Bishop/Knight promotion.

| policy | complete tied choice count | source utility interval | exact source regret interval |
|---|---:|---|---|
| geometric_half |1|[1,1]|[0,0]|
| linear_mixture |1|[1,1]|[0,0]|
| unit |12|[0,1]|[0,1]|

This is actual independent source-label discrimination, unlike the price-blind
Pawn-risk trees. It proves contact removes the adverse source-labelled tie
members here; **not** strict gain against every possible unit tie breaker.
A unit tie breaker choosing Queen/Rook or a King move also achieves1. Under
an explicitly hypothetical uniform tie lottery unit's mean is10/12, whereas
contact's is1; no deployed/random-world lottery has been justified.
Any fixed weights with Queen strictly above P/N/B/R yield the same selected
move, so this does not identify either contact law's detailed relative prices.
No comparison against tuned human prices or stronger production engine occurred.

Original source association failed before probes: the reused native-only
FEN guard correctly rejects Pawn-origin promotion. Original producer/raw
remain intact. V2 corrects current-piece board association while preserving
local origin/promotion/history separately. Same root/all choices/policies;
cumulative24 local transitions,21 author pushes,48 list entries,24 outer
DTM/WDL calls,0.094seconds for V2. Original local0.063seconds separately;
no labels in original and no repeated successful batch or cap reset. V2 uses
the same source inventory for all methods. Source files are verified by a
separate final integrity check rather than a claim of V2 after-close checking.

Raw: data/threepiece_promotion_use_20261006.json (retained failure),
data/threepiece_promotion_use_v2_20261006.json (success). See frozen
THREEPIECE_PROMOTION_USE_PROTOCOL.md and explicit correction document.
This is an adaptively motivated development control, not a natural-population
holdout or independently selected formula test. Root immediate boards/history
agree, but source eventual no-50-move utility is not automatically local F24F:
B/N children are source automatic draws and locally ongoing. No complete
future-game bridge, full local WDL or general strength/material-price claim.
Next useful work is mixed-inventory certificate coverage and a decision-changing
complete equal-resource comparison; repeating positive promotion examples adds
little information. Old closed reference trials and Xiangqi holdout stay untouched.
