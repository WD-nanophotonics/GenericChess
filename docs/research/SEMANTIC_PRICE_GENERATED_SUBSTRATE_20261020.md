# Semantic price on a generated-rule substrate — 2026-10-20

## Question and method

Does the geometry-only semantic profile bridge change a cross-piece price in a
real generator-produced ruleset after one existing semantic action is
recombined onto a generated mover?

Generate seed21, board size4, bilateral-random setup with hybrid movement
enabled. The generator emits legacy-only movement-atom types; source inspection
shows its `RuleSet` constructor does not populate `semantic_actions`. Preserve
that generated ruleset as control. In the candidate, add the existing
compound-shift action to its generated P type. This is one synthetic
recombination on a generated substrate and a profile-only diagnostic; no
position/search/game was run. The profile intentionally projects only the
direct leap and does not price the companion shift.

## Result

The generated rule has non-anchor types P, X, A. Their control raw capability
scores are P0.272396, X3.579028, A2.015892; the candidate P score is0.813828,
while X and A are unchanged. Median raw capability remains A in both arms.
Normalized board values are:

| Type | Control | Candidate |
|---|---:|---:|
| P | 135 | 404 |
| X | 1775 | 1775 |
| A | 1000 | 1000 |

The normalized P:X ratio changes from0.07606 to0.22761 (+199.26%). In this
example the generated P had legacy leaps `(-3,+2),(+3,+2)`; the candidate adds
eligible direct leap `(+1,+1)`. This confirms that semantic geometry can move
relative normalized price inputs on one generated-rule substrate after a
synthetic semantic recombination.

## Limits and implication

This is not evidence that the base generator produces semantic actions, that
the price is useful, that compound-shift opportunity is represented, or that
the result generalizes across generated rules. It supports retaining the
geometry bridge as a provisional input when semantic actions are explicitly
recombined, while keeping utility and full-domain validation open. Exact rule
fingerprints, type signatures and all values are in
[`data/semantic_price_generated_substrate_20261020.json`](data/semantic_price_generated_substrate_20261020.json).
