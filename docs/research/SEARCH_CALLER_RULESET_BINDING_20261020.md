# Public AlphaBeta ruleset-binding contract — 2026-10-20

## Question and decision

Does the public AlphaBetaPlayer.choose_action(session, limits) reject an ongoing
GameSession created for a different generated RuleSet? A player owns a compiled
RuleSet; accepting another RuleSet's position could search under the wrong
movement, promotion, drop, and terminal semantics.

## Evidence

Source inspection found two guarded routes. The already-finished-session fast
path in generic_chess/ai/alphabeta/player.py calls ensure_ruleset_match
before returning TERMINAL. An ongoing call enters run_root_search, which
constructs SearchPathRuntime; its constructor also calls ensure_ruleset_match
before initializing search state. This preserves the ruleset-bound caller
contract without adding an API-level duplicate check.

A bounded public-call probe used two distinct generated 5x5 hybrid RuleSets
(seeds 20261020/20261021) and passed the second's ongoing session to a player
bound to the first. It raised RuleSetMismatchError before search. The exact
reproducer and output are in data/search_caller_ruleset_binding_20261020/.
Existing tests/product/test_finished_session_search.py covers terminal fast-
path mismatch rejection; this probe covers the ongoing route. No source change,
new regression test, games, or training was needed.

## Scope

This closes only the public caller's ruleset-binding invariant. It does not
claim arbitrary concurrent direct SearchPathRuntime mutation is supported,
or certify all generated rules. The controller and search entry remain bound to
the session's matching compiled RuleSet; no interface/API change is warranted.