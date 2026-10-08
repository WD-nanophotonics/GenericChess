# Exact geometry occupancy and rectangular capability

The default geometry profile now uses `generic-v2`: exact expected pseudo-target
counts for the existing independent-occupancy model and supported Leap/primitive
straight Ray atoms. This fixes an observed representation defect, without fitting
human prices or claiming that mobility is material utility. Raw opportunity,
normalization, rounded prices and search effects remain separate quantities.

Evidence and recovery: [data index](data/geometry_occupancy_20261009.json) and
[archive manifest](../archive/geometry_occupancy_20261009/index.json).

## Observed defect and correction

On a3x2 board, equivalent capped rays2 and999 with the same additional leap
produce identical target unions in4374 occupancy/source controls. The old64-draw
fallback nevertheless produces different curves because its seed includes the
textual movement signature. A common occupancy seed repairs comparisons within
that sampled branch, but cannot repair the analytic/sampled branch boundary:
adding a redundant one-step leap to a pure ray gives0.640625 instead of0.625
at density0.5 in the recorded common-seed diagnostic. This is approximation noise
triggered by representation, not a behavioral change or a position-model failure.

For a source and endpoint, write its nonzero displacement as `m*u`, where `u`
is a primitive integer vector and `m` a positive integer. This decomposition is
unique. Every supported ray reaching the endpoint requires the same `m-1`
intermediate landing squares to be empty; a direct leap removes that requirement.
Retain the minimum required prefix length `k` for each distinct endpoint.
With independent empty/friendly/enemy probabilities `1-rho`, `rho/2`, `rho/2`,
its expected contribution is `(1-rho/2)*(1-rho)^k`.

Linearity of expectation permits summing endpoint contributions even when their
events share squares. Integer counts by prefix length, sorted accumulation and
one histogram per density curve remove duplicate/order/sampling dependence.
General distinct paths with different blocker sets cannot use minimum length
alone. Cannons, blocked-leg moves, state guards and compound effects are outside
this primitive formula; the separate semantic projection keeps its own scope.

Twenty complete tiny-board occupancy enumerations agree with the product formula
within1e-10. The non-axis5x3 control with primitive direction(2,1) checks actual
landing prefixes rather than Manhattan distance: a short redundant leap changes
nothing; a direct leap to(4,2) changes that endpoint's density0.5 contribution
from0.375 to0.75. Default curves do not invoke the retained explicit sampler.

## Migration and interface scope

The default version changes from `generic-v1` to `generic-v2`, invalidating old
default profile caches. An actual project-local old-Shogi-cache control misses
under the new default and then hits its new cached result. Historical sampled
outputs remain pinned in the archive; changing the version label alone does not
restore the old algorithm. Explicit Monte-Carlo helpers remain diagnostic APIs.

Standalone capability analysis and its memory cache accept `BoardShape`; area,
width and height replace square-only indexing. A square shape shares the existing
integer-size cache key; transposed rectangles have distinct keys. Before the
exact-law migration,15 frozen square profiles matched the shape extension
exactly. Final v2 integer/shape and atom-order curves also match exactly, while
old sampled values intentionally change and pure arithmetic may differ by
floating-point roundoff. Final rounded board/hand tables match all six separately
recorded exact-prototype profiles.

This does not enable rectangular default evaluation. Its first old failure was
missing `piece_types` on the geometry carrier; further dependencies include drop
masks, promotion zones and dynamic attack/escape indexing. The public default now
reports that scope explicitly and directs callers to a supplied evaluator.
Rectangular Core execution with supplied evaluators remains supported. Native
rectangle support and the App Control blocked Native candidate remain unqualified.

## Scoped caller and cost observations

Chess's six prototype curves agree with the prior analytic result. Shogi's
promoted Bishop/Rook curves and several generated hybrid curves lose sampling
noise; median normalization can also change other types' rounded prices.
No human reference labels or Xiangqi holdout were read.

Four existing event roots receive eight cold Core calls at D2/8192nodes/5seconds,
q2/hard8. Pinned old versus exact board prices keep reference hands, ordering and
dynamic weights. All first choices and PVs agree; three pairs complete D2 and
the previously capped pair remains D1. Different scores are sensitivity, not
playing improvement. Final histogram refactoring preserves these exact rounded
inputs, so the capped callers were not rerun merely to refresh a report.

The earlier task-law ablation's sole different-choice root was also tested at
requested D3 with the original equal budget. All four calls cap after D2; this
does not establish D3 stability. A producer text replacement accidentally made
four earlier calls q3 as well as D3. Those outputs remain preserved, explicitly
excluded from the intended D3/q2 comparison, with the correction in a new file.

One intrusive five-second profile of the existing capped Core root records
28792 attacked-square calls/3.032s cumulative versus2666 availability calls/0.589s.
It also records millions of budget checkpoints. This identifies S3 safety queries
as a concrete cost, not a timing benchmark or permission to weaken cancellation.
A separate72-query static count has2405 target misses in2484 geometry visits and
no actor-incompatible visits. It does not support another actor-prefilter index.

The advisor independently reviewed the old published movement/mobility source
and supplied the non-axis control. It did not execute the new local measurements.
The reply was read completely and adopted; no publication approval was required.
