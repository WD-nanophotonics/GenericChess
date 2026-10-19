# Two-type semantic movement price composition — 2026-10-20

## Question and construction

Can an eligible direct semantic movement geometry change a normalized
cross-type static-price ratio when more than one non-anchor type is present?

The starting point is the existing `weird_rulesets()[3]` compound-shift
fixture, `move_and_shift_adjacent_friendly`, whose R has four legacy orthogonal
rays and an eligible direct leap `(+1,+1)` that also shifts a companion piece.
For this explicitly synthetic profile-only composition, add an independent
non-anchor N with the ordinary eight knight leaps. Keep the same RuleSet fields
and piece list in both arms; the control compiles the legacy-only declaration,
and the candidate adds the existing semantic action. No board/search/game
outcome was run. The companion shift remains outside the geometry-only feature.

## Result

| Type | Raw control | Raw candidate | Normalized control | Normalized candidate |
|---|---:|---:|---:|---:|
| R | 9.0879148631 | 9.7665291154 | 1307 | 1340 |
| N | 4.8157025256 | 4.8157025256 | 693 | 660 |

The normalized R:N ratio changes from `1.8860` to `2.0303` (about `+7.65%`).
This establishes that the current median-normalized bridge can shift a relative
price input in one controlled two-type composition; it does not establish that
the shift is useful, robust across mixtures, or a better exchange price. The
result is synthetic and depends on the profile's median normalization and the
geometry-only treatment of a compound action.

Exact atom signatures, fingerprints and raw/normalized outputs are preserved
in [`data/semantic_price_two_type_composition_20261020.json`](data/semantic_price_two_type_composition_20261020.json).

## Limits and next decision

This is not a generated-rule sample, game-utility test, search test, or
validation of companion-shift valuation. It answers the narrow normalization
question, so consider a distinct generated composition only if it can change
whether this profile bridge should remain a provisional candidate. Do not
infer broad price quality from this one fixture.
