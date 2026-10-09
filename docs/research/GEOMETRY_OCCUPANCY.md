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

## Pure empty-cell guards and joint options (2026-10-09)

The opt-in semantic candidate is now `semantic-opportunity-v2`. It accepts one
finite state-predicate subset: `count==0`, any owner/type/promotion, board
location, one exact source-offset ref, with no subject or that same subject.
The latter two encodings count the same occupied square. Other state guards,
slot/zone guards, postconditions and compound effects stay explicitly excluded.
This changes the opt-in input projection, not the default `generic-v2` builder.
The supplied-rule comparison records its actual version and no longer builds an
unused default profile before constructing the requested candidate. Old reports
retain their original versions and outcomes.

The occupied source is a contradiction; a quiet target is already empty; an
enemy target contradicts emptiness. Off-board exact refs match no occupants in
Core and therefore count zero. Duplicate guards and overlaps with path-clear or
counted-path cells are joint occupancy events, not independent multipliers.
The research prototype matches1620 finite event/density controls and444 actual
Core endpoint/transition controls across nine cases. Product/Core regressions
also cover equivalent global and same-subject encodings. No own-anchor safety,
complete legal mobility or full Xiangqi valuation follows from this projection.

On the internal9x10 horse definition,16200 Core pseudo-attack positions match an
independent eight-offset/leg oracle. All16 H quiet/capture patterns are included;
the global and same-subject versions have identical signatures and curves. At
the declared equal weights on density0/.125/.5/.875/1, guarded raw is2.557639
versus unguarded4.233333; each density curve is `(1-rho)` times its free-leap
curve. Palace/river guards remain excluded: G/A/E have no included board patterns,
and S includes only forward movement. These exclusions are unsupported scope,
not evidence of zero value. No Xiangqi human holdout was read.

A first ordinary four-root lexical-history cohort was uninformative: all16
D2/D3 calls complete, but changing only H leaf lookup1->1581 at the old scale
changes none of its eight paired choices/scores. This remains a negative
sensitivity result. A separately declared exchange is preflighted to contain H
capture and actual R/N recaptures. Semantic B removal puts B into hand, while
legacy H recapture removes it from the game; the real forced material delta is
`boardB+handB-H`, not `boardB-H`. The two failed preflight assumptions and
corrections are retained. At fixed other leaves/ordering/dynamics, the H-only
intervention changes that delta+1->-1579 and D2 capture value-3671->-5251.
Full-width D2 and public q0 agree; eight D2/D3/q0/q2 calls complete with restored
roots/PVs. D3 q0 defers the capture to its horizon and scores-3670 for both,
whereas q2 still distinguishes. This is executable input sensitivity, not a
material calibration or playing-strength gain.

A joint-options diagnostic exposes another compression loss without changing
the context law. On7x7, eight blocked-leap endpoints share four cardinal empty
prerequisites, or use eight distinct neighboring prerequisites. Every endpoint
still needs exactly one empty square, so all five complete source-averaged
opportunity curves agree exactly. Their signatures differ because the rules
really differ. At the central source, quiet/capture count means at rho=.5 are
2/1 for both, but the probability of at least one quiet move is.847412 versus
.899887; at least one capture is.627471 versus.656391. Shared guards increase
count variance.69632 prerequisite/target assignments per one-step diagnostic
and1088 actual Core endpoint-set controls qualify this scoped result.

For `q=1-rho` and target availability `p` (`q` for quiet, `rho/2` for capture),
the central no-option probabilities are `[rho+q*(1-p)^2]^4` versus `(1-q*p)^8`.
These are one-step unit-task quantities, not travel time, WDL or a replacement
price. A declared uniform fixed-colored-stock law retains the distinction:
seven7x7 stocks have exactly equal mean counts but different any-option
probabilities. At12 enemies/12 friends among48 non-source squares, source-
averaged capture means are both.625271, while any-capture probabilities are
.456365/.475313. Exact subset unions are checked against24 tiny colored-layout
censuses. This adds conditional information; it does not identify the right
context/task/response law or justify another default coefficient.

Sixteen separate existing7x5/9x10 caller cells qualify supplied material-only
and semantic-mobility-only evaluators at q0/q2, initial/one-move roots. All
complete D2 within8192 nodes/5sec and restore state/history/witnesses/PVs. These
are narrow execution controls, not rectangle default pricing or Native support.

Recovery: [guard data index](data/semantic_guards_20261009.json) and
[guard archive](../archive/semantic_guards_20261009/index.json). Raw Slack/user
records stay private; original failed/undiscriminating outputs are preserved.


## Finite zone inputs and source-law diagnosis (2026-10-09)

Opt-in `semantic-opportunity-v3` adds source/target membership in compiled finite
zones, inside or outside, independently of occupancy. Other square-reference
kinds, slots, state identities, postconditions and compound effects remain
excluded. The inverse owner-frame square test agrees with Core's rotated zone;
complement/outside and duplicate zone encodings preserve signatures and curves.
Default generic-v2 generation/cache and square-only candidate-profile metadata
are unchanged. Raw projection works on rectangles; a full rectangle profile does
not follow. Flying-general target-identity conditions remain unsupported.

Before integration, a private v2 adaptation matches16740 actual Core pseudo-
attack positions against independent palace, river, elephant-eye and coordinate
oracles. Under the declared equal mass at densities0,.125,.5,.875,1, G/A/E/S raw
opportunities become.2/.133333/.422917/1.341667. These are projected counts, not
material values; G remains an anchor with zero profile lookup. Product tests add
720 actual5x3 source/target/owner/occupant contexts, both owner-relative and
absolute zones, inside/outside, plus independent transition and encoding checks.

This exposes a separate approximation: all-board source averaging includes
squares outside a restricted actor's movement component. A diagnostic retains
that original law and reports uniform forward closure from initial on-board
sources, not initial SCCs or a chosen mixture of components. Complete RuleSet
input can include initial placement; dependence on that input must remain
separate from dependence on single-actor movement alone. Initial support unions
sources without duplicate weighting. Thirty actual Core source positions and
four transitions verify a three-layer forward chain; its terminal zero remains
in the closure mean2/3, rather than being filtered into mean1.

Xiangqi G has9 reachable sources, A5, E7 and S55 under the restricted graph.
A's palace graph has two SCCs of sizes5/4; E's45-source own-half graph has eight
components, so conditioning merely on nonzero movement differs from initial
forward closure. Soldiers cross multiple SCCs: their initial SCC alone would
lose genuine forward capability. The cross-game conditional table is in
CROSS_GAME_PRICE_DIAGNOSTIC.md. None proves full-game reachability: transformations,
drops, own-anchor safety and history are outside this graph.

A declared5x5 rare-bridge counterexample prevents silently adopting uniform
forward-support weighting as the new default. An actor starts in a three-node
chain; an optional bridge opens a20-node orthogonal region. At density.5, sixteen
independent empty prerequisites make bridge eligibility1/65536. All-board raw
changes1.92->1.920000457764, while uniform-closure raw jumps.5->2.086957019308,
because every positive bridge probability changes the closure from3 to23sources.
All138 actual Core blocker/target controls agree. Positive geometric support
loses transition likelihood; this finite diagnostic does not refute all lifetime
models or prove which source law is materially relevant. Keep support and
conditional means descriptive, with no new default/material claim.

Core execution also avoids allocating an owner-1 rotated zone tuple for every
candidate: inverse-transform the one resolved square and test the original zone.
No zone cache, new index, altered checkpoint or legality boundary is introduced.
Six actual lexical-route Xiangqi positions retain all legal actions, both attack
sets,518 child transitions and identical checkpoint counts in48 alternating
legal-list pairs. Local median old/new ratios range.9681 to1.0005; these short
calls support only a modest descriptive cost observation.

Sixteen actual cold public Core D2 calls (initial/one legal action, q0/q2,
2alternating repetitions, old/inverse) all complete within8192nodes/5seconds,
retain every non-time decision/work field, restore roots/history/witnesses and
replay PVs. Unit leaf and ordering prices, disabled dynamics and root tactical
policy stay fixed. Per-cell paired wall ratios range.9639 to1.0070, including one
small regression; no general speed, strength, Native or default-price claim.

Recovery: `data/semantic_zones_20261009.json` and
`../archive/semantic_zones_20261009/index.json`. Frozen v2 guard evidence remains
in its original archive. Producer preflight errors are retained; no raw account
records, private inputs or absolute traceback paths enter this package.

A separate finite-horizon diagnostic preserves bridge probability under an
explicit kernel: propose uniformly among24other cells, accept the projected
quiet/enemy event, otherwise stay. Six25-state chains through256steps match
1536independent four-state aggregate recurrences. With16guards the mean
opportunity over256steps is.187309338, versus.187216054 for the impossible
bridge; region mass at the last sampled state is9.11e-5. A coupling bound
scales with horizon times bridge probability, so finite-horizon continuity
avoids the existential-support jump. This is a feasibility control: proposal,
stay, density, initial source and horizon are assumptions, with no opponent,
transformation or natural occupation model. It selects no source law or price.
The first aggregate oracle omitted enemy-target acceptance; its failed producer
is retained and corrected validation supersedes the premature local checkpoint.

Exact sources, failed preflights and outputs for this zone/source/cost supplement
are routed by `data/semantic_zones_20261009.json` to the separately recoverable
`docs/archive/semantic_zones_20261009/index.json`; the earlier v2 archive stays
immutable.


## Explicit rectangle candidate profile bridge (2026-10-09)

The next interface check removes the square-only opt-in profile restriction.
The candidate reads typed semantic support metadata and uses BoardShape.area
for existing drop-freedom diagnostics. It no longer needs the legacy inspection
handle for type IDs, anchor flags or promotion-target IDs. Raw opportunity,
normalization, rounding, hand scaling and promotion-gain conventions stay the
same; no new price or source law is selected. Drop diagnostics still summarize
legacy geometry, not the utility of semantic drop effects.

Four whole-profile/scope comparisons on Chess/Shogi with two configurations
exactly match187b58f. The first preflight incorrectly counted internal9x10
Xiangqi as square; the old builder correctly declined it. Final16cold Core D2
calls cover7x5/9x10 cannon,5x3 zone and internal9x10 Xiangqi roots, q0/q2,
two repetitions each,8192nodes/5seconds and q2hard8. All complete, repeat,
restore roots and replay legal PVs; q0 scores match same-evaluator full-width
references. Leaf/ordering candidate prices and Core attack authority are shared.
These are interface controls, not a candidate strength comparison.

The supplied-rule diagnostic also reports default-input scope via the existing
type map, rather than missing rectangular piece_types. Rectangle callers must
explicitly disable anchor-escape/promotion dynamics; Core attack mobility can
remain enabled. Unsupported dynamics fail with a scope-specific error, not a
silent weight change. Default generic generation and Native rectangle support
remain separate unsupported boundaries. Candidate version remains v3 because
its opportunity formula and square outputs did not change.

Recovery: [rectangle profile index](data/semantic_rectangle_profile_20261009.json)
and [archive](../archive/semantic_rectangle_profile_20261009/index.json).

A separate preflight checks126actual transitions at the internal-Xiangqi root
and finds two legal cannon-captures-horse/recapture lines. With all dynamics
disabled, unit material is0->1000->0; v3 is0->1428->-2126. Actual hands stay empty,
unlike the earlier mixed-semantics guarded-H witness. This establishes that the
rectangle candidate table reaches a real exchange. It is sensitivity, not a
claim that the selected prices or resulting search policy improve. Sources and
outputs are supplemental files in the same rectangle archive; its zip is unchanged.

## Fixed-order leaves, finite source laws and inert custody

The fixed-order internal-Xiangqi exchange separates leaf prices from ordering:
unit ordering is fixed for both unit/v3 leaves, Core D2, q0/q2hard8,
8192nodes/5seconds, two cold repeats per cell. All8calls complete and restore
roots/PVs. Full-width q0 scores are unit0 versusv3-1428; q2 scores both0.
The v3 capture/recapture contrast is1428 then-2126. A changed choice or horizon
response demonstrates sensitivity, not an improvement or a calibrated price.

A declared finite-source model uses the same reward but two proposal kernels:
uniform24other cells versus uniform local geometry, with blocked proposals
retaining their probability.3072 finite-horizon aggregate controls pass.
For the connected20-cell region, exact stationary means differ:93/40=2.325
versus303/124=2.4435483871;40stationarity and800detailed-balance checks pass.
A16-empty-guard bridge has expected first entry2097216 versus87384proposals.
Positive bridges eventually enter; an impossible bridge never does. Longer
horizons do not identify a natural source law and can restore a rare-bridge
discontinuity. No new default law or longer compute campaign follows.

Partial-profile controls remain explicit: a temporal transform changes material
0 to-1604 while auxiliary state changes; a four-cell compound shift keeps1000.
Their effects are excluded. Nifu/no-mate drops can retain identical candidate
tables because drop legality/utility is not projected. Reversing compiled
patterns on Chess/Shogi/internal-Xiangqi/cannon under default and non-dyadic
density laws gives8exact profile/curve/signature matches; no rounding rewrite.

An actual no-drop/no-declaration8x8 rule exposes inert custody credit: two
captured victims both have current typeR but promoted basesP/Q; old v3 hands
give257/900 while the board opportunity values areP286/Q1000/R3286. Under
matched fixed ordering,8D1/D2 old-scale/zero-hand calls agree with same-evaluator
full-width minimax. D1 credit disappears with zero-hand; D2 remains-3286.
This is a known useless-stock coefficient, not a tactical-strength claim.

The opt-in builder now labels a narrowly proved subset
`semantic-opportunity-v3-inert-hand`: zero hand coefficient only if all drop
masks are false, declarations/auxiliary mechanisms are absent, and every
remaining executable pattern is within the known simple board projection.
Dead all-drop patterns may be ignored only under those false masks. Unknown
guards/effects retain the legacy, explicitly unvalidated hand scale. A proposed
legacy-only predicate was rejected locally: the same public lowering gave0
versus900. The final typed IR/support predicate agrees without the inspection
handle. Raw board curves/normalization do not change; default evaluation/cache
does not invoke this opt-in candidate. Real hands, keys and history stay intact.

No-drop alone is insufficient. An actual optional include_hands declaration
crosses LOSS(score0) to WIN(score1) after the same capture and reply, while
remove_from_game stays LOSS on the identical physical board. Dot independently
located this published-baseline dependency; the local Agent executed the
counterexample and new product controls. Any declaration conservatively excludes
zero-hand classification. General hand utility remains unresolved.

Exact producers, failed preflights, partial outputs and final controls:
[leaf/source/custody index](data/leaf_order_20261009.json) and
[recovery manifest](../archive/leaf_order_20261009/index.json).

Final1758active regressions pass after the shared-IR/version-report correction;
17affected report/boundary tests also pass separately. The72archive members
were extracted into an isolated project-local recovery tree and every hash
matched. Raw private-path failure logs stay local; redacted failures/partial
outputs are retained publicly, not recast as successful runs.

A final8-pair transfer against actual53e41df source preserves all raw curves,
board tables and promotion gains on Chess/Shogi/internal-Xiangqi/cannon under
both density laws. Canonical Chess/Shogi/internal-Xiangqi hand scales stay
unchanged/unvalidated; only the proved-inert cannon coefficients change.
This is retained as a manifest supplement without altering the72-member zip.

The safe subset is deliberately conservative at whole-rule scope. In a mixed
legacy rule, a real four-ply prefix captures P/Q into stock while only Q has a
legal drop mask. The classifier retains the old P coefficient900. A hypothetical
P-stock removal at that reached root preserves18one-ply actions/physical boards
and Qstock, but changes identity; that counterfactual is not certified reachable
or equivalent in repetition/history. This exposes a possible per-type extension,
not a deployed fix or permission to remove stock from state. A focused follow-up
must decide whether that extension pays for its extra dependency reasoning.

Four fixed-order D1/D2 old-scale versus supplied P-zero searches at that mixed
root match their full-width references. Scores13278 versus12378 differ by900,
but every nontiming/non-score decision/work field stays equal: Qdrop atb2,
nodes19/58. Pstock is constant on these shallow nonterminal frontiers. This
witness does not justify a new per-type production classifier merely to remove
a score offset; seek a decision-changing failure first. No identity merging.
