# Public search fallback from a checked root — 2026-10-20

## Question and scope

When an already-cancelled request reaches the public `AlphaBetaPlayer` caller
with its side to move in check, does the caller still receive a legal evasion,
and is the caller's session left unchanged? The source constructs its initial
fallback from runtime legal actions before honoring the cancellation budget;
the existing public tests checked generic legal fallbacks and quiescence
evasions separately, but not this combined caller contract.

## Bounded probe

`data/search_checked_root_fallback_20261020/verify.py` builds the existing
4x4-rook check fixture, seeds that valid ongoing state into a test-only
`GameSession` fixture, snapshots state/history/record/search witnesses, and
calls `AlphaBetaPlayer.choose_action` with a pre-cancelled token. No product
code, game, training, or search setting changed. The fixture uses private state
seeding only because `GameSession` intentionally has no arbitrary state setter;
it does not imply support for such a production mutation API.

The root was in check with two legal evasions. The public call returned one of
those evasions with `result_source=legal_fallback`, `termination_reason=cancelled`,
zero completed depth/nodes and an empty PV. The complete session snapshot was
unchanged. Exact fields and ruleset fingerprint are in `data/.../result.json`.
The focused regression run `pytest tests/product/test_ai_search.py tests/product/test_finished_session_search.py -q` passed all 62 tests; pytest
emitted only a cache-write permission warning for `.pytest_cache`.

## Conclusion

This closes only the pre-cancelled checked-root fallback contract for the
fixture. It found no public-call defect or reason to change the search interface.
It makes no general latency, search-strength, generated-domain or all-history
claim. Continue with a distinct decision-changing question rather than
expanding cancellation/fallback coverage without a concrete uncovered caller.
