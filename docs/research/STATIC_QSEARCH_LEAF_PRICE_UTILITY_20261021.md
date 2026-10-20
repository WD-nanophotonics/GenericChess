# Qsearch stand-pat leaf-price utility — 2026-10-21

## Question and frozen contrast

On eight fresh generated 5x5 rules (seeds 622115–622122), does changing only
the candidate's non-check qsearch stand-pat leaf score from Unit material to
static-v2 improve finite-budget utility or robust candidate-side search cost
against a fixed Unit opponent? The frozen panel used two 3/4-ply roots per
rule, both candidate owners, D3/8192 nodes/0.5 seconds/qdepth 2/qnode 128, TT
off, Unit main-search leaves and normal Unit ordering. Qsearch ordering was
disabled identically. Complete state, promotion/drop semantics, history and
the existing legal-action interface were preserved. The 64 physical games
are 32 matched root/owner pairs; they are not 64 independent rule samples.

The q-leaf proxy is installed only across the public quiescence call and its
recursive runtime, then restored in `finally`. In-check nodes use mandatory
evasion search without standing pat; terminal/declaration returns remain
unchanged. Main-search evaluations and capture/promotion ordering remain Unit.
The outcome-free 16-root preflight recorded q-leaf calls in both arms and a
same-state score difference in 14 roots (minimum 8); all 32 arm evaluation
counts matched, with zero searched actions submitted and zero outcomes.

## Execution and integrity

The first post-search root guard was a harness false positive: `GameSession.history`
is a tuple, but the producer compared it with `list(session.history)`. A
one-root diagnostic found state, position, history contents, result and search
witnesses unchanged. The producer now snapshots the tuple and reports
field-specific changes. No outcome or submitted action preceded the repair.
The plan records this pre-outcome amendment and binds the updated producer hash.

All 64 slots completed in 55.328 seconds (49.529 seconds summed search-caller
time); 53 reached actual terminal results and 11 remained UNKNOWN at the
frozen 48-candidate-ply horizon. Every UNKNOWN retained that reason. There were
0 invalid actions and 0 full-history replay mismatches. Full records, roots,
rules, profiles, per-move traces, plan, producer, preflight and result are in
`data/static_qsearch_leaf_price_utility_20261021/`.

## Results

| View | Matched pairs | Static-v2 minus Unit conservative mean interval |
|---|---:|---:|
| Overall | 32 | [-0.03125, 0.65625] |
| Owner 0 / owner 1 | 16 / 16 | [0.0625, 0.6875] / [-0.125, 0.625] |
| 3-ply / 4-ply roots | 16 / 16 | [0.125, 0.875] / [-0.1875, 0.4375] |
| Candidate first / reply | 16 / 16 | [-0.3125, 0.5625] / [0.25, 0.75] |

The eight leave-one-seed-out lower bounds were `-0.0357, +0.1071, -0.0714,
-0.1071, -0.1429, +0.0714, +0.0357, -0.1071` in seed order. Thus the
predeclared strictly-positive utility gate failed overall and in several
strata. Static-v2's 32 candidate games had 16 wins, 7 draws, 6 losses and 3
UNKNOWN; Unit had 7 wins, 10 draws, 7 losses and 8 UNKNOWN. The paired audit
retained 22 both-known pairs, 7 Unit-only UNKNOWN, 2 static-only UNKNOWN and 1
both-UNKNOWN pair. Every UNKNOWN pair was bounded independently; none was
converted to a draw. The uneven censoring and seed/role variation prevent a
strength or population conclusion.

For each arm, a known W/D/L is `[+1,+1]`, `[0,0]`, or `[-1,-1]`; UNKNOWN is
`[-1,+1]`. Each matched contrast is the static interval minus the Unit
interval, and view bounds are arithmetic means of those pair intervals. Cost
reduction is `1 - static_candidate_nodes / Unit_candidate_nodes` per pair;
the listed value is its median within each registered view.

The cost result was large in this limited regime: median paired candidate-node
reduction was 68.65% overall, 67.81%/71.25% by owner and 67.81%/71.25% for
3-/4-ply roots. Candidate-side caller time summed to 6.119 seconds for
static-v2 versus 13.068 for Unit. Whole-game caller totals were 23.833 versus
25.696 seconds, respectively; these also include the fixed-policy opponent
searches. The cost portions of both retention gates passed, but the required
nonnegative utility lower bounds did not. Candidate first actions differed in
15/32 matched pairs, which establishes exposure only.

## Decision and limits

Neither preregistered retention gate passed. Keep static-v2 q-leaf prices out
of defaults; close this sampled q-leaf consumer and do not top up or repeat its
seeds. The result supports a substantial candidate-side node-cost reduction
under this exact depth/budget and a materially changed action set, but not
robust finite utility. It is not evidence about other boards, search budgets,
full WDL, strength, or generic rule populations.

The incoming Chat suggestion to test the optional Python `StagedMovePicker`
is a distinct consumer: unlike this q-leaf contrast, it can use both
`capture_order_value` and promotion `type_value` while keeping Unit leaves.
The existing default-order and qsearch-order panels do not test that opt-in
path. Treat the comment as advice, not authorization or a default change. A
small no-outcome isolation preflight can decide whether that distinct route is
worth a fresh, separately frozen finite panel; no outcomes should be collected
unless it demonstrates actual hook exposure and candidate-action differences.
