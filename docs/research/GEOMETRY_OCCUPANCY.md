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

## Consistency and explicit-evaluator followup

The [consistency supplement](../archive/geometry_occupancy_20261009/consistency-index.json)
retains subsequent producers, failures, raw results and final caller replay.
Twenty-four square primitive families/120 density cells match the independent
semantic path projection within2.3e-16, including hybrids previously omitted
from that regression. Fifteen rectangular families/75 density cells also match;
2600 actual Core attack positions agree with an independent primitive oracle.
This does not equate pseudo-attacks, legal captures and material utility.

A second representation defect was demonstrated: balanced forward/backward
leaps have asymmetry0, but duplicating the forward atom gave1/3. Their canonical
cache key is identical, so the first insertion determined later diagnostics.
Asymmetry now counts unique destinations. This field does not enter current raw
price weights, so its correction alone changes no static prices.

The active short anchor-escape heuristic also counted duplicate atoms and used
owner0 offsets for owner1. Mirrored forward-only anchors scored1 instead of0;
duplicating the atom raised that to2. It now reuses owner-relative unique target
tables, constructing only the short subset for mixed anchors. Its existing
empty-destination/short-step/current-attack scope remains a heuristic, not legal
escape or complete semantic anchor movement. No positional term/weight is added.
The first helper implementation increased local escape-call cost; the final
table implementation retains136 existing route counts with lower microbatch
time. This is not a whole-search speed claim.

Disabled promotion setup no longer reads square-only metadata. With supplied
price tables, material-only Evaluator works on7x5/9x10 carriers. The existing
Core SemanticAttackEvaluator also works with semantic mobility enabled and
anchor/promotion terms disabled. Four D2 controls match full-width references,
preserving roots/PVs. Default rectangle profile generation and the remaining
square-dependent dynamic configurations remain unsupported; Native stays
unqualified. These are explicit evaluator configurations, not new defaults.

A16-call leaf-table x ordering-table factorial includes changed hand prices,
unlike the earlier board-only ablation. All four roots retain their first choices;
three complete D2 and one remains D1/time-limited. Final table-based replay of
all four full-v2 callers retains those choices/scores/PVs and completed-root work.
Changed leaf scores are sensitivity, not strength. A separate declared15sec/
8192-node D3 resource point for both old task-law tables reaches node_limit after
D2. The old5sec records remain intact, D3 stays unknown and no further extension
was triggered. This negative result does not gate independent development.

## A concrete opportunity-compression limitation

On the supported independent occupancy law, an ordinary rook and one-screen
cannon have identical quiet counts. For a directed ray with L available targets,
L>=1, write q=1-rho. Rook capture expectation is `(1-q^L)/2`; cannon capture is
`[1-L*q^(L-1)+(L-1)*q^L]/2`. Their difference is `L*rho*q^(L-1)/2`.
The L=0 case contributes0. This is a finite ray-boundary term, not a material
value formula. Three rectangular semantic rules agree with21 density controls.
At rho=.5, C/R total opportunity ratios are about.787 on5x3, .851 on7x5 and
.912 on9x10. Formula-only100x100 analysis gives.993; no large board was compiled.

Requiring s screens contributes `choose(k,s)*rho^(s+1)*q^(k-s)/2` at an endpoint
with k intermediate cells. For any fixed s and positive rho, an infinite ray's
capture sum tends to1/2: eventually the required occupied screen(s) and next
occupied endpoint occur, whose owner is enemy with probability1/2. Thus zero,
one and two-screen mechanisms retain different actual prerequisites while their
source-averaged total opportunity converges. Nine finite mechanism cells/45
density controls agree, with486 Core pseudo-attack and486 separate actual legal
quiet/capture controls; accepted actions were applied and parents preserved.
The first scalar-attack oracle used reversed arguments and an incorrect target
occupant condition; that failed producer assertion and its correction are kept.

This exposes a specific loss when compressing prerequisite structure into one
opportunity count. It does not prove that static prices are useless, that these
mechanisms have equal utility, or which material ratio is correct. Retain quiet,
capture and prerequisite/context components before proposing another utility
compression; do not fit a replacement to human prices or require WDL first.

A retained component supplies one next direction: the capture endpoint-distance
moment, using ray landings rather than Manhattan distance. Conditional on an
available enemy endpoint, the infinite-ray mean is `(s+1)/rho`, so the mechanisms
remain distinguishable even when capture counts coincide. Thirty-six finite IR
controls agree; formula-only100x100 at rho=.5 gives about1.980/3.958/5.936 for
zero/one/two screens, tending to2/4/6. Zero capture mass has undefined conditional
distance, recorded as null. Distance is neither travel time nor utility; this
component is retained for task compression, not multiplied into a new default.
