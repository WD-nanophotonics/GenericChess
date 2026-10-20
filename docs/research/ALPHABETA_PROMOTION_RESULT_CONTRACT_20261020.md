# AlphaBeta promotion result contract

## Question

Does the public AlphaBeta result preserve a selected promotion target through
its principal variation, GameSession submission, and serialized replay?

## Evidence and result

The existing fixture exposes four legal root actions, exactly one of which is
the promotion `e7-e8=G`; its earlier search test checked only legal membership.
The strengthened regression uses a fixed evaluator that prefers the child with
the promoted type, then checks that AlphaBeta returns a `BoardMove` with target
`G`, places the promoted piece in the child state, and keeps that exact action
at the head of the principal variation. The action is submitted through
`GameSession`, serialized/deserialized, and replayed; complete state and result
match.

Focused validation: `python -m pytest tests/product/test_ai_search.py
tests/product/test_promotion.py -q` — 49 passed. Search implementation is
unchanged; no all-promotion-target or generated-domain claim follows.
