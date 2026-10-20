# Static-v2 capture-order utility on the default AlphaBeta path — 2026-10-21

## Decision

Close this sampled capture-order candidate. The preregistered 64-game panel showed real same-state action changes and lower aggregate candidate-node use, but neither retention gate passed: conservative reward bounds are not strictly positive in every owner/parity/leave-one-seed-out view, and paired median node reduction is zero. Keep the current candidate out of defaults; do not repeat this panel or infer broad strength.

This test changed only the candidate's `capture_order_value`. Both arms used the same leaf evaluator, fixed Unit opponent, roots, search limits and full-history validation. The tested path is the ordinary `MoveOrderer`: `SearchTuning()` leaves `use_staged_move_picker=False`, and the UI's AlphaBetaPlayer construction uses that default. This does not test the optional staged-picker benchmark profile or promotion `type_value` ordering.

## Frozen panel and integrity

Plan: [capture-order-plan.json](data/static_capture_order_utility_20261020/capture-order-plan.json), SHA-256 `85853ba786ebfb81922e3df38867edfe001425f023fc68624b0cefcc9695ed3b`. Preflight SHA-256: `349ec86c67670b3db060226034c1c6514385779fed144d137084ecbb8b359eea`. The panel used eight generated rules, 16 fixed 3/4-ply roots, both candidate owners and both capture-order arms (64 games, 32 paired root-owner units).

All 64 slots completed. There were 61 actual terminals and three retained `HORIZON_48_CANDIDATE_UNKNOWN`; the three remain censored. Invalid actions: 0. Complete-history replay mismatches: 0. The generated game-record SHA-256 is `8290f2a888738bae57b02e29291fcada2932fe1346bc40ebadb68872e8408b96`. No game was added for this analysis.

The [public evidence bundle](data/static_capture_order_utility_20261020/) contains the exact plan, preflight, rules, roots, all 64 game records, raw run receipts and analysis scripts/results.

## Results against the prespecified gates

| View | Paired units | Conservative reward difference, static − Unit |
|---|---:|---:|
| Overall | 32 | [+0.0625, +0.2500] |
| Candidate owner 0 | 16 | [+0.1250, +0.2500] |
| Candidate owner 1 | 16 | [0, +0.2500] |
| 3-ply roots | 16 | [0, +0.1250] |
| 4-ply roots | 16 | [+0.1250, +0.3750] |
| Leave-one-seed-out minimum lower bound | 7 seeds/view | 0 |

Gate A required strictly positive lower bounds in every listed view, including every leave-one-seed-out result. It failed on owner 1, 3-ply roots and two leave-one-seed-out views. Among 29 pairs with both outcomes known, static won two, Unit won none and 27 tied; three other pairs remain UNKNOWN. Pairwise transcript comparison found 11/32 candidate choices differed at the same state. Of those, two pairs favored static, six tied and three remained UNKNOWN. An order-induced choice change therefore occurred, but is not itself a utility claim.

| Candidate search cost | Unit capture order | Static-v2 capture order |
|---|---:|---:|
| Candidate nodes, total | 689,388 | 490,172 |
| Candidate caller seconds, total | 73.594 | 54.059 |
| Capture-order hook calls by candidate arm | 60,539 | 59,215 |

Static-v2 used 199,216 fewer candidate nodes in aggregate, but paired candidate nodes were lower in 11 pairs, equal in 8 and higher in 13; the median paired fractional reduction was 0 overall and in every owner/parity stratum. Gate B required at least 10% median reduction in each of those views, so it failed. The aggregate saving is heterogeneous, not a robust per-pair result. Leave-one-seed-out node savings range from a large benefit to a reversal.

The hook did run in the candidate searches. Across both arms the fixed foe generated another 119,708 capture-order calls. `type_value` was called zero times, so this panel gives no evidence about promotion-target ordering. The optional staged picker remains a distinct route and was not silently conflated with this result.

## Chat advice and scope

The 2026-10-21 PRIMARY comments independently advised a minimal order-only comparison, fixed leaf values/opponent/budget, and separate recording of hooks, actions, costs and W/D/L/UNKNOWN. This panel did that for the default `MoveOrderer`; the action-trace audit adds the observed 11/32 same-state choice divergences. The cautions against equating changed order with improved strength or changing defaults are supported.

The other comments concern DEV_AUX's rule-15 root-pool preparation and task2625 UNKNOWN-censoring profile. They remain that role's work; PRIMARY neither edits its checkout nor duplicates those analyses. The optional comment list is not a task assignment.

## Limits and next step

This is a finite generated 5x5 sample on one default Python AlphaBeta ordering path. It does not establish a population effect, all-rule value quality, promotion-order utility, staged-picker utility or a global price/default change. Close this exact sampled candidate. Resume the generic price-transfer mainline by choosing a distinct, decision-changing consumer from current evidence; do not rerun these roots or open another order panel absent a changed premise.
