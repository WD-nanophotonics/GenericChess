# Static-v2 board values with promotion potential — 2026-10-21

## Question and frozen contrast

When the existing rule-derived promotion gain is disabled versus enabled, does it add finite-budget utility to the scoped static-v2 board candidate? The frozen 64-slot panel changed only `promotion_potential_weight` from 0 to 3. Both arms shared the same static-v2 board profile, Unit hand values, promotion-gain table, capture/type ordering, dynamic terms, legal rules and fixed Unit-hand/bonus-off foe. Search used public Python AlphaBeta, D3/8192 nodes/0.5 seconds, qsearch depth 0 (hard cap 8), TT off, staged picker off, and the same root pruning setting.

The plan fixed eight generated 5x5 seeds (622099–622106), 16 deterministic roots with 9- or 12-ply prefixes, both candidate owners, and 64 physical games. All slots, actual terminals and UNKNOWN outcomes are retained; the decision is scoped to this static candidate and cannot change the global evaluator default.

## Audited result

The independent audit regenerated all eight rules and profiles, replayed 64 full game histories from 16 roots, and found zero invalid actions, replay mismatches or unstarted slots. There were 52 actual terminals and 12 horizon UNKNOWN slots. In the 32 exact root/owner pairs, 26 had comparable first-candidate states and none changed its first action. All 26 resolved reward differences were zero; six pairs had UNKNOWN in both arms.

| View | Pairs | UNKNOWN pairs | Conservative reward bounds | Median node reduction |
|---|---:|---:|---:|---:|
| All | 32 | 6 | [-0.375, +0.375] | 0.0% |
| Owner 0 | 16 | 3 | [-0.375, +0.375] | 0.0% |
| Owner 1 | 16 | 3 | [-0.375, +0.375] | 0.0% |
| Odd prefixes | 16 | 2 | [-0.25, +0.25] | 0.0% |
| Even prefixes | 16 | 4 | [-0.5, +0.5] | 0.0% |

Every leave-one-seed-out interval also crosses zero. The preregistered utility gate therefore fails; the 10% cost gate fails. Aggregate candidate nodes were 449,302 off and 448,787 on, while candidate seconds were 63.673 off and 65.093 on; caller seconds were 126.801 and 128.163. These small work/time differences are descriptive, not a strength or timing claim.

## Interpretation and limits

Do not retain the promotion-potential bonus inside this sampled 5x5 static-v2 candidate on this evidence. This does not show promotion distance is generally valueless, alter the global evaluator weight, or reject static-v2 board values. It is distinct from the Unit-board bonus study: here the board price candidate was fixed in both arms, isolating the bonus contribution in that context.

The independent replay audit passed. The analysis script's first invocation printed the summary but failed on its final write to `run/analysis.json` with a real `PermissionError`; no file changed. A read-only re-execution skipped only that final write and reproduced the stored summary. Exact diagnostic is private at `.local_agent/static-promotion-bonus-audit-20261021.json`.

Provenance: plan SHA-256 `91F12E3C7F6B8027ED1060647F572234049785F7ABB0A50A8947F63BE9066191`; games SHA-256 `BE89BE5DE696E8D12FD095FB8F06720822E08B95AACCF58B029FFEC484576D88`; analysis SHA-256 `3BA2B3652720B9D6A6BFDAC6BF3763194C66CF124AEEAE5CEB634FC58C65EA04`. The complete plan, rules, profiles, roots, games, receipts and audit scripts are in `data/static_board_promotion_bonus_utility_20261021/`.
