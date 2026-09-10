# GenericChess F66 analytic fixed-feature output correction

Work order: `GENERICCHESS-F66-ANALYTIC-FIXED-FEATURE-OUTPUT-CORRECTION`

Parent repository SHA: `691bf70c33848f6c547bc0884ea0c7f658073582`

This is a zero-training, zero-search linear-algebra analysis. It uses only the
frozen Gen1 width-32 parameters and the 96 cached F62 action rows. No optimizer
epoch, seed sweep, Arena, self-play, tree search, teacher search, external
engine, Heavy job, or checkpoint materialization was performed. The detailed
transient result is in the ignored file
`.generic_chess_flow/f66-analytic-fixed-feature-output-correction/fixed_feature_correction.json`.

## Fixed-feature direction

The Gen1 input mean, input scale, hidden weights, hidden bias, target scale, and
output bias are frozen. At root 44, let `a` be the Gen1 top action and `t` the
stable/ordinary cached teacher-supported target:

* `a = P [2,4]->[2,3]`
* `t = P [0,4]->[0,3]`

Let `h_a` and `h_t` be the existing Gen1 hidden activations and
`d = h_t - h_a`. The fixed one-dimensional output-layer family is
`w(beta) = w_Gen1 + beta*d`. The root-44 score gap at beta zero is
`Q_t - Q_a = -144.54987551964768`, and `||d||^2 = 1.3680110838188686`.
The exact equality breakpoint is

`beta_44 = -(Q_t-Q_a) / (target_scale * ||d||^2) = 0.14492290213387557`.

All cached action scores are affine in beta, so the remaining results use exact
line intersections and upper-envelope transitions, not a beta grid.

## Breakpoints and safe interval

The same F65 stable/ordinary criteria were recomputed: 24 high-confidence roots
are the Gen1 margin upper quartile (`4,648.7751151083285`), and 84 roots are
stable and ordinary usable.

| quantity | exact beta |
|---|---:|
| first top-action change anywhere | 0.144922902134 |
| root-44 required tie/flip | 0.144922902134 |
| first unsupported change | 1.740628460696 |
| first high-confidence change | none before the analyzed positive envelope |
| supported corrections before unsafe | 1, root 44 |

The first unsafe change is root 72: the Gen1 top
`B [7,1]->[6,2]` moves to `S [5,1]->[6,2]`, while the cached teacher remains
the original bishop action. Therefore the nonempty safe interval is
`[0.14492290213387557, 1.740628460695656)`. Applying the fixed midpoint rule
gives:

`beta* = 0.9427756814147658`.

At beta*, exactly one cached root changes: root 44 moves from `a` to `t`.
The change is diagnostically teacher-supported; no unsupported change has
occurred and all 24/24 high-confidence Gen1 top actions remain unchanged.

## Size and implementation cost

The maximum absolute output residual change over all cached actions at beta* is
`1,187.9361058408865`. Gen1's maximum residual magnitude is
`20,303.186769489927`; after the correction it is `20,513.10326173877`.
This is a small local correction, not a return to the roughly 240k
replacement-child scale.

Materialization would only replace the existing Gen1 `output_weights` vector
with the deterministic width-32 vector `w_Gen1 + beta* d`. No schema change,
Native evaluator change, additional component, or inference-cost increase is
needed. This report does not materialize that vector or create a checkpoint.

## Final classification

`FIXED_FEATURE_OUTPUT_CORRECTION_FEASIBLE`

The existing Gen1 representation can express the one useful cached correction
with a single output-layer perturbation. The next authorized step, if approved
by Courier, is one deterministic width-32 child checkpoint using seed 59011's
already selected root-44 target and the fixed beta above; no training run is
needed to construct it.
