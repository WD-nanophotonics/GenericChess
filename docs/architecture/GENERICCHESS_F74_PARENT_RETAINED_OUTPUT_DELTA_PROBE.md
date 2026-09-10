# GenericChess F74 parent-retained output delta probe

Work order: `GENERICCHESS-F74-PARENT-RETAINED-OUTPUT-DELTA-PROBE`

Baseline repository SHA: `ecf4e6e0acca399dba8f4cea0607d5cfe9cef89c`

This bounded experiment froze Gen1 checkpoint
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4` and used
only persisted F62 fit evidence plus the 20 stable F62 development roots.
The hidden representation, input normalization, target scale, output bias,
hand-type binding, perspective, and Native scale were unchanged. Only the
width-32 `output_weights` vector was corrected. The final holdout split was
not read.

## Deterministic fit

The required trust filters recomputed to 34 trusted fit roots from the 48-root
F62 fit split. Their 246 retained action rows produced 212 consensus-versus-
alternative ranking pairs. Each root contributed equal total weight. A single
deterministic regularized convex pairwise-logistic fit reused Gen1's recorded
regularization `0.001`; it used no random initialization or tuning grid.

The raw fitted output-weight delta had L2 norm `7.217303780437056` and maximum
absolute coordinate `2.5936274700993893`. The fit objective decreased from
`0.18157913934932665` to `0.10485746007146873` at the fitted direction and at
the final trust-region-scaled candidate (`alpha* = 1.0`).

The exact positive safety boundaries were:

| boundary | value |
|---|---:|
| high-confidence top-action boundary | `2.117168204393398` |
| residual magnitude boundary | `5.246734610172431` |
| final `alpha* = min(1, 0.5*high-confidence, residual-cap)` | `1.0` |

On fit cached action rows, Gen1's maximum residual magnitude was
`18043.408509768706`; the candidate maximum was `15236.193717174776`, below
the allowed `36086.81701953741`. Candidate checkpoint identity is
`bafabe1a6eeedf30b0ebe34109e5c4efdad87fc434edf8e75e9030e958bca0bb`.

Representation identity guards passed: the candidate model SHA is
`f29d7f7108c35e85ed66aa9b77f3bea8fcce1f7e4a51ede5f1923107f5b2ea69`, and only
`output_weights` differs from Gen1. The eight sampled Native/Python fixed-point
residual comparisons were exact.

## Development deployment

Each of the 20 stable development roots ran fresh parent and child engines,
each arm repeated once, with root-window pruning enabled, an 8 MiB TT, a
2,048-node limit, max depth 12, and zero qsearch depth. All 40 repeated arms
were deterministic and completed depth 2.

The child changed 6 of 20 actual search decisions. All six were lateral
changes: `toward-deep = 0`, `away-from-deep = 0`, and `lateral = 6`. Parent and
child deep-consensus agreement were both `2/20`. This diagnostic does not grant
teacher or strength authority.

## Classification

`PARENT_RETAINED_OUTPUT_DELTA_DEPLOYMENT_VISIBLE`

The output-only correction is visible to the current product search under the
authorized budget. No production evaluator/search adaptation, promotion, or
follow-on strength test was performed. The ignored machine-readable evidence
is `.generic_chess_flow/f74-parent-retained-output-delta-probe/f74_results.json`.
