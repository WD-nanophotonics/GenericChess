# GenericChess F65 exact blend breakpoint feasibility

Work order: `GENERICCHESS-F65-EXACT-BLEND-BREAKPOINT-FEASIBILITY`

Parent repository SHA: `d6263fecc316bfc44956920253635f48ef8d00a8`

This is an algebra-only analysis of the 96 cached F62 action rows and frozen
Gen1/59011/59012/59013 outputs. It ran no training, optimizer epoch, Arena,
self-play, search, teacher search, seed generation, alpha grid, external
engine, or Heavy job. Detailed transient arithmetic is in the ignored file
`.generic_chess_flow/f65-exact-blend-breakpoint-feasibility/blend_feasibility.json`.

## Exact safe-prefix definition

The high-confidence set was recomputed from the cached Gen1 top-two margins:
the upper quartile is `4,648.7751151083285`, containing 24 roots. A teacher
action counts as diagnostically supported only when the existing F60/F62
criteria hold: spectrum top-10k equals top-20k, the root is ordinary usable
(not in a mate band), and the new top action equals the cached q20k teacher
top. This is diagnostic evidence, not strength authority.

For each root/action pair, the blend was treated as an affine line. All exact
pairwise line intersections were used only to construct the upper-envelope
transition sequence; no alpha grid was sampled. A safe prefix requires every
high-confidence Gen1 top action to remain unchanged, each lower-confidence
change to be a supported teacher correction, and no corrected root to later
leave that supported action.

## Decision-relevant breakpoints

All three directions are algebraically feasible under that definition, but each
has only one supported correction before its first unsafe transition:

| child | first top change | first supported correction | first unsafe change | supported corrections before unsafe | safe interval | fixed midpoint alpha* |
|---|---:|---:|---:|---:|---:|---:|
| 59011 | 0.001637403150 | 0.001637403150 | 0.006992954730 | 1 | `[0, 0.006992954730)` | 0.004315178940 |
| 59012 | 0.001663741927 | 0.001663741927 | 0.007015652303 | 1 | `[0, 0.007015652303)` | 0.004339697115 |
| 59013 | 0.001712790027 | 0.001712790027 | 0.006941697581 | 1 | `[0, 0.006941697581)` | 0.004327243804 |

The useful correction is the same cached root for every direction: root 44
moves from Gen1 `P [2,4]->[2,3]` to the stable/ordinary cached teacher
`P [0,4]->[0,3]`. At each fixed midpoint alpha*, root 44 is the only changed
root, all 24 high-confidence Gen1 actions remain unchanged, and the change is
teacher-supported. The next transition is unsupported, so the prefix ends
there.

The selection rule therefore chooses exactly one direction: seed 59011. Each
direction has one supported correction; after that correction, the remaining
safe widths are approximately `0.005355551580` (59011), `0.005351910376`
(59012), and `0.005228907554` (59013), so 59011 wins on the prescribed
numerical-width tie break. This is only a virtual evaluator specification; no
production checkpoint is created.

## Exact representation cost

Gen1 and every child are distinct width-32 `CompactNonlinearResidual` models
with different input means, input scales, hidden weights, hidden biases, and
output weights. Therefore their exact affine residual blend is not another
width-32 network by parameter interpolation.

The input normalization can be absorbed into each hidden unit's affine
weights and bias. Concatenating the 32 parent hidden units and 32 child hidden
units would then represent the blend exactly as a width-64 single network,
with output weights scaled by `(1-alpha)` and `alpha`. This is an algebraic
reparameterization in theory, but it is not an existing supported runtime
representation: the current native validator accepts only width 16 or 32.
Thus exact blend reuse needs a wider/multi-component runtime extension; it is
not runtime-cheap, and no such extension is implemented here.

## Final classification

`BLEND_REUSE_FEASIBLE_BUT_RUNTIME_EXTENSION_REQUIRED`

The chosen virtual direction is seed 59011 at `alpha*=0.004315178940`, but it
must not be materialized or tested as a checkpoint under this work order. The
next mechanism remains a parent-initialized bounded update in the existing
width-32 runtime, subject to a separate design decision comparing that small
warm-start change with the cost of a width-64 or multi-component extension.
