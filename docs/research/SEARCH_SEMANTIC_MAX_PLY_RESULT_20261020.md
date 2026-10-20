# AlphaBeta evaluates a generated semantic max-ply child — 2026-10-20

## Question

Does public AlphaBeta search treat the generated rule's `max_ply` adjudication
at a searched child as a draw, rather than evaluating that child position?

## Fixture and result

Use the existing generated semantic fixture `weird_rulesets()[2]` with only its
`max_ply` set to 1. The ongoing root has three legal actions; Core submission of
each action reaches `MAX_PLY`. A side-preferring evaluator would score a
nonterminal child at +/-1234, but public AlphaBeta completes depth 1 with score
0, a legal selected action, and `main_iteration` result provenance. The input
session's complete record is unchanged.

The new focused regression and the whole max-ply module plus adjacent
AlphaBeta search, terminal, and provenance tests pass.

## Consequence and limits

This verifies one generated semantic child-horizon contract and supplies a
durable public-caller regression where only Core boundary coverage existed. No
search change was needed. It is not a claim about all generated rules, native
backend equivalence, strict real-time behavior, or max-ply utility beyond the
configured draw result. Do not expand horizon tests without a distinct
observed contract.
