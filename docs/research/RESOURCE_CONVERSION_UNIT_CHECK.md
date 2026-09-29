# Rule transitions account for tokens, not material exchange rates

**Unknown.** Can legal promotion, capture, and capture-to-hand transitions
supply a common, game-independent material unit through resource conversion?

**Proposed principle and falsifier.** Represent each full semantic position by
a vector of owner, board type, and hand base-type counts. A legal action has an
exact inventory difference `d`. If a transition were a cost-free, reversible
exchange between fungible resources with equal strategic utility on both
sides, `w·d=0` could constrain an exchange rate. The smallest falsifier is one
rule-legal transition that changes location, side to move, ownership, or
future options while changing the inventory: then `w·d=0` is an *extra*
indifference assertion, not a consequence of legality.

**Direct semantic check.** The existing executable cross-game capture fixture
`tests/test_ruleset_capture_disposition.py::test_capture_disposition_matches_public_core_and_semantic_executor`
uses public and semantic transitions on the same explicit positions. Its three
cases establish:

| Ruleset | Observed inventory transition | Additional state change |
| --- | --- | --- |
| Western Chess | Opponent pawn leaves the game; capturing rook moves to its square. | Turn, board geometry, history. |
| Standard Shogi | Opponent promoted pawn leaves the board; capturer gains an unpromoted pawn in hand; rook moves. | Custody, type/mode, turn, board geometry, history. |
| Xiangqi diagnostic | Opponent soldier leaves the game; capturing rook moves. | Turn, board geometry, history. |

Chess promotion likewise replaces an on-board pawn with one selected target
type (`Q/R/B/N`) as part of a move. Standard Shogi promotion changes board
type while preserving base identity; later capture can demote that token into
the opponent's hand. None of these is a reversible, context-preserving trade
at declared indifference. A conserved *token identity* is useful accounting,
but treating one pawn token and one promoted pawn token as one strategic value
would conflate custody, location, and legal options. In remove-from-game
captures, even token count across the board is not conserved.

The necessary condition for a conversion-derived rate fails before numerical
measurement: legal transition stoichiometry alone does not supply utility
equality. A rate could be estimated only after declaring a context, choice
model, and payoff or indifference criterion; those are the assumptions the
static-prior derivation currently lacks. This rejects the *cost-free
conversion-unit route*, not all rule-informed material approximations.

**Verification.** The capture fixture passed all three cases on 2026-09-29
(`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp
.local_agent/pytest-resource-conversion tests/test_ruleset_capture_disposition.py
-k capture_disposition_matches_public_core_and_semantic_executor`). It is a
local, hand-built transition contract and does not establish initial-position
reachability or full ruleset completeness. Its assertions compare public and
semantic postpositions and hand disposition. No material references, Xiangqi
values, or numerical coefficient selection enter this check.

**Next lead.** Investigate a deployment-independent *dimensionless* structural
prior with an explicit, externally motivated loss for what it approximates,
or identify a different source of cardinal scale. Predeclare the comparison
contexts and normalization; test representation and context robustness on a
small synthetic case before Chess validation. Do not reuse entropy or feature
counts merely as a default valuation.
