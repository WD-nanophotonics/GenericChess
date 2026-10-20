# Retain the last complete iterative-search result — 2026-10-20

## Question

When cancellation arrives after one completed depth but before the next begins,
does the public AlphaBeta result retain the completed action, score and PV?
This is an anytime-result contract for unfamiliar generated rules, distinct from
the no-completed-iteration fallback and interrupted completed-root-win cases.

## Bounded check

A deterministic injected abort at the depth-2 boundary was compared with a
fresh depth-1 control. On a generated 4x4 ruleset (seed43), both returned the
same depth1 action, score2814 and PV; the interrupted call reported
`termination_reason=cancelled` and `result_source=main_iteration`. This is one
small generated ruleset, not an all-domain or timing claim.

A product regression now injects cancellation before the next iteration on the
existing small rook fixture, and asserts equality of the completed depth,
source, action, score and PV plus root-state immutability. The focused
`test_ai_search.py`, `test_search_result_provenance.py` and
`test_completed_root_win.py` set passed. The experiment showed the current
implementation already retains the result; this closes a test-coverage gap and
does not justify a search-policy/backend change.

## Decision and limits

Keep the documented last-complete-iteration behavior. The test proves one
deterministic abort boundary and one fixture contract; it does not establish
all cancellation timings, wall-clock guarantees, or equivalence across
backends. Do not add a new result API field. Continue to a distinct uncovered
generated-search caller contract.
