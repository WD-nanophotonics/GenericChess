# Per-type median multiplicity sensitivity — 2026-10-20

## Question and method

The static profile normalizes each non-anchor raw capability value by the
median across non-anchor `PieceType` entries. Does adding one repeated type
score to that median change the normalized values of the existing types?

Using only the eight already-saved 5x5 candidate96 profiles (522001–522008),
the source formula was recomputed in memory. For each of the 24 existing
non-anchor types, its raw score was appended once to its own ruleset's median
inputs; the 72 original type values were then compared with the saved profile.
Board rounding/clipping and the existing 0.9 hand multiplier were applied.
The ordered input files' concatenated SHA-256 is
`6e2387c301fb83430322ebbc03b34ecba184de085ef2dafa7404183148d53940`.

## Result and limits

46 of 72 existing board/hand value pairs changed. Maximum absolute changes
were 4560 board points and 4104 hand points. This confirms that a
per-type median's scale depends on the type multiplicity in its ruleset; it is
a formula counterfactual, not evidence that the duplicated type is reachable,
that a value is strategically better, or that a game decision/outcome changes.
The eight saved profiles have no exact repeated non-anchor movement-signature
class within any one ruleset. The generator builds profiles independently for
each type ID and does not impose a cross-type signature uniqueness check, but
this scan does not estimate how often generated rules actually collide.

No games, searches, training, source changes or defaults were involved. Keep
the current profile unchanged; do not infer utility or a generated-domain
frequency. A revisit needs an observed reachable within-ruleset duplicate and
a decision-changing consequence.

## Existing generated-rule duplicate — profile 521005

The prior exact-signature audit identifies two non-anchor types (`A` and `P`)
inside saved profile 521005 with the same movement signature. The profile SHA-256
is `4846b4c2e6d647ec4ae8c919ebaaa3132a9590f4a520c22b257311049873335c`.
Its saved all-type raw median is 3.023645996; taking one representative per
signature class gives 2.804477276 (7.815% lower). Recomputing with that
alternative class median changes all three existing board values
`A/B/P: 1000/855/1000 -> 1078/922/1078` and hand values
`900/770/900 -> 970/830/970`.

This is an observed saved-rule sensitivity to the reference-set definition,
not evidence that signature deduplication is the correct estimator. `A` and `P`
remain semantically distinct types (promotion metadata differs), and the
all-type median may intentionally weight rule types rather than unique
geometries. No decision/outcome comparison was run. Next compare these two
frozen profiles on the existing 521005 root set at identical search limits;
do not play new games or change the normalizer unless outcomes support a
decision-relevant conclusion.
