# Physical coupling, requested depth and relative leaf prices

This segment follows the user-confirmed pure-Leaper forward-design direction.
PRIMARY owns these generated-rule/controller experiments; AUX truth and learning
work is not repeated. The prototype retains complete rules and histories but is
limited to plain Leap movement, capture removal and no promotions, drops or extra
semantic actions. The complete generated domain remains the long-term target.

## Physical FLOOR coupling

The old label-cycle experiment is CLOSED and is not replayed. Its first
AB/FLOOR path differences often occurred at FLOOR because the same random index
selected different physical actions from permuted legal lists. An explicit
`physical_type_xy_v1` probe now sorts actual legal actions by mapped type and
coordinates. It checks the full rule domain, a total anchor-fixed type bijection
and unique physical keys. Omitting the option preserves the literal old policy,
including its early winning-action scan. Sorted winning actions can differ from
the old first winner; they have the same immediate terminal payoff, not the same
deterministic action law.

All four fixed validation layouts and their label cycles were frozen before
32 new games, both roles and FIRST2 streams. Expected loop cost was 300 seconds,
with the unchanged 600-second cap. Sixteen new cost returns passed the screen;
the loop completed in 128.452 seconds, with 1,242 controller returns and no
UNKNOWN. Shared-Core replay checked all 32 records and 2,403 PV edges.

Of 16 matched physical pairs, 11 have identical complete action histories. Five
first diverge at AB, but none changes the winning side/draw. Two select different
immediate wins among seven available wins. The other three have the same saved
score and completed depth 4 at the 512-node boundary, without retained root-argmax
sets; their tie explanation remains UNKNOWN. Mapped-trace qualification checks
637 frontiers, 34,354 history entries and 4,123 physical action ranks. These are
reached-trace results, not all-state policy covariance, WDL or a variance-reduction
guarantee. The control does not select a favorable label or refill old slots.

## Requested depth is distinct from node budget

A new 96-game control uses all 16 original ABC rules, three adjacent pairs,
both roles and one deterministic execution per seat. D1/D2/D3/D4 are explicit
requested depths with the same 8,192-node safety ceiling, q0 and forced-check
hard depth 8. These are not repeated independent seed samples.

| Pair | Finite signed utility | Higher-depth role0 | Higher-depth role1 |
|---|---:|---:|---:|
| D2/D1 | 5/32 | 7/16 | -1/8 |
| D3/D2 | 3/16 | 11/16 | -5/16 |
| D4/D3 | 1/32 | 9/16 | -1/2 |

The loop took 68.920 seconds. All 96 games and 2,821 returns are retained, with
6,263 legal PV edges. Fifty-four root-immediate-win returns have depth0; every
other return reached its requested depth, with no safety-node interruption.
Only one exposed code has all three positive two-seat means, and no code has
strict gains in both roles on all links. Do not promote a strength chain or new
benchmark from these finite, seat-sensitive means. The original node-budget
controls remain separate rather than being renamed as depth experiments.

## Relative price controls and costs

The new direct price comparisons use the same three-method adapter and Static
ordering on both sides. UNIT assigns each non-anchor board type 1000 and hand
type 900. MOBILITY counts distinct empty-board destinations over the actual finite
board, scales by the ordinary-type median to 1000 and rounds; hand prices are
0.9 times board prices. Anchors remain 0. Static dynamic/promotion fields and
median are retained. Capture removal makes hands unreachable, but their full
explicit tables are still saved. No exposed labels or outcomes fit these prices.

All 32 existing conditional ABC layouts and both roles are used for each of
Static/UNIT and Static/MOBILITY: 128 new games, with expected 2,400 seconds and a
3,000-second cap. Before fitness, 192 new cost returns and 1,262 exact evaluator
material-difference checks passed. An independent destination-set census checks
all frozen mobility inputs.

The registered cost decision uses the actual old 64-game whole-loop time,
1,159.336 seconds, doubled for 128 games, plus new preparation/preflight costs.
The caller's separate maximum-sampled-call forecast is retained unchanged in
`preflight-sampled-max-forecast.json`; it is not a future-call bound. The named
whole-game screen was registered before queries, rather than chosen after
fitness. Neither method changes the cap or guarantees full coverage.

The two-board continuation was registered while the4×4 experiment was still
running. All 32 layouts are mapped onto BOTH5×5 and6×6 via coordinates
`(0,1,n-2,n-1)`, without rejecting the one initial-win layout on either board.
The resulting 64 full inputs retain all nongeometry rule fields; profiles,
legals and finite-board prices are recomputed, while old4×4 graph summaries are
explicitly marked as parent metadata. Two price pairs and both roles produce
256 planned executions under ONE 4,200-second cap, expected 3,000 seconds.

Its 192 initial and192 additional full-prefix cost returns are all new. The
64 uniform 8-ply prefix draws include four terminal draws, retained in full;
only their immediately preceding states are used for cost queries. Fitness
still starts at the original full initial records. Exact price decomposition
checks total 3,712. The registered whole-game forecast, including these costs,
is 3,020.536 seconds. Sampled-call forecasts and original registrations remain.
Timings include ordinary concurrent validation/computation and do not imply
exclusive-hardware speed comparisons. No cap is extended to fill missing slots.

The 4×4 loop is now CLOSED in1,397.123 seconds:128/128 games,
5,894 controller returns, no UNKNOWN, and25,700 replayed PV edges.

| 4×4 pair |Finite signed utility|Static role0|Static role1|W/D/L for Static|
|---|---:|---:|---:|---:|
|Static/UNIT|7/64|3/16|1/32|12/47/5|
|Static/MOBILITY|0|3/32|-3/32|7/50/7|

Static/UNIT changes 18 of 32 role-swap trajectories and 7 physical winning-side/draw
outcomes; Static/MOBILITY changes 2 trajectories and no such outcome. All8 pairs
with identical reachable board prices have identical full action histories.
These are finite exposed utility observations. The positive UNIT contrast
shows that counting alone did not match Static on this cohort; it does not
establish population significance, optimal prices or a learner requirement.
The zero MOBILITY contrast does not prove that all relative prices are useless.

The 5×5/6×6 combined experiment is CLOSED: 256/256 games, 16,865
controller returns, no UNKNOWN and a 3,004.319-second loop under the original
4,200-second cap.

| Board | Static/UNIT | Static role 0 / role 1 | Static/MOBILITY | Static role 0 / role 1 |
|---|---:|---:|---:|---:|
| 4×4 | 7/64 | 3/16 / 1/32 | 0 | 3/32 / -3/32 |
| 5×5 | 1/16 | 1/4 / -1/8 | 0 | 1/8 / -1/8 |
| 6×6 | 1/32 | 3/32 / -1/32 | 0 | 1/32 / -1/32 |

On 5×5 and 6×6, UNIT role swaps preserve respectively 12/32 and 12/32 full
paths, and 25/32 and 26/32 physical winning-side/draw outcomes. MOBILITY preserves
30/32 and 32/32 paths, and all outcomes on both boards. All eight new no-op pairs
have identical full histories; combined with 4×4, all 16 such controls pass.

Static has a modest positive finite UNIT contrast on each board, but role 1
reverses on the larger boards. MOBILITY retains zero finite contrast here.
Neither result establishes population strength, optimal relative prices or an
absence of learning space. Board, starting layout and default profile change
together across envelopes. The shared normalized median does not separately
identify price ratios versus position-dependent material scale. Keep the cheap
forward controls; no product evaluator, sampler or learner is activated.

An interval containing zero, or identical choices on exposed roots, cannot prove
that relative prices have no learning space. No learner gate, quality scalar,
Elo claim, product evaluator or sampler default is changed.


## Next executable step and verification scope

The sole exposed code with three positive adjacent-depth means is `(5,12,8)`.
Its FIRST3/4 metadata-admitted layouts have full inputs and 16 new cost returns;
12 future games are **NOT RUN**. The sampled forecast is 146.857 seconds under
an unchanged 180-second cap, distinct from the original 30-second empirical
expectation. This is selected-code layout-outcome replication, not an independent
rule holdout or benchmark promotion. A copied old 96-game/1800-second stop sentence
was corrected before fitness to match the already-frozen numeric 12/180 plan;
original registration/preparer bytes and the diagnosis remain. No input, query,
expected result or numeric budget was changed.

Across this segment the four current batches plan 512 physical executions and
all 512 finish. There are 26,822 controller returns. The 672 new preflight returns
include the 16 next-design calls; they do not imply 12 future games were played.
Old label, M0 and public-packet references remain old evidence. Distinct literal
GameRecords are descriptive, not independent sample sizes.

Cold preflight means a fresh Player/TT on each saved root within the same
process. Process/native/profile setup, query order, per-call time and whole-loop
time remain distinct. The two cost methods were fixed before queries. The
rounded old5×5 timing in the prose gives 2,966.784 seconds; the stored full-
precision timing gives 2,966.812448 seconds and was used in the actual pre-fitness
3,020.536-second gate. Both are preserved; the 0.028-second difference changes
neither cap nor execution.

Verification is composed of complete original-game history/PV replays, exact
exported value and original-file-hash equality, full input/profile/source and
all 672 cost-PV checks, plus a literal exported FLOOR-stream replay on the 32
new coupling records. It does not claim to rerun every exported game a second
time or provide an independent engine/WDL oracle. The old 368-record public packet
also passed a full changed-reader compatibility replay. Full technical evidence
and exact scope are in [the evidence directory](data/leaper_coupling_prices_20261023/README.md).


The final packet contains 282 distinct literal final records, not 512 independent
samples. Exact-copy review checks 50 original files, 16 source capsules, 122 full
input/profile instances and all 672 cost returns/2,076 cost PV edges. Original
full replays cover 89,117 PV edges; the exported coupling subset independently
checks 616 literal FLOOR choices. The full compressed packet SHA-256 is
`70680df2ed2da76aa0cf8b6a1de59413f0076bbc37dd6d8d6d746fa6c0367197`.
