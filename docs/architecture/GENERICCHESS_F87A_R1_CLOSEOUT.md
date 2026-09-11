# F87A-R1 closeout

Work order: `GENERICCHESS-F87A-R1-QUALIFICATION-CALIBRATION-SEMANTICS-CORRECTIVE`

Baseline and published checkpoint: `bbcc4319d48c4e78fb0224218feedec500f33389`

## Corrective outcomes

- Added a single reducer with `qualification_target=PLAYABILITY`, required Layers A-C, separate integrity and qualification gates, layer reason codes, and consistent overall status.
- Expanded Layer B to anchors and ordinary types, both owners, per-opening-source reachability, component diversity, SCC/sink/reverse diagnostics, and semantic applicability statuses.
- Reused shared movement graph/SCC/reachability/type-profile primitives from F86N instead of maintaining a second census implementation.
- Reused the frozen F86L authority for F86I terminal-template transport; the known insufficient-transport counterexample is visible in the report.
- Canonicalized Common-Tape legal-action ordering, stored seat assignment/winner/score/action-sequence/final-position evidence, and marked one-opening sensitivity `UNMEASURED`.
- Corrected `CENSORED` score contamination: censored games have null scores and do not enter side-bias denominators.
- Added tracked compact ledger: [GENERICCHESS_F87A_R1_CALIBRATION_LEDGER.md](GENERICCHESS_F87A_R1_CALIBRATION_LEDGER.md).

## Result evidence

The raw/generated JSON remains ignored by policy. Its synchronized local hashes are:

| Evidence | SHA-256 |
| --- | --- |
| `artifacts/f87a_ruleset_qualification/manifest.json` | `b0c2079b3e6d316817e48adfb9553629d894fc2c62297f4d5c837f24ff59611b` |
| `artifacts/f87a_ruleset_qualification/summary.json` | `cacc67e8a7fc299a182e9f7e68556fbe34dc5bd7c504072af93ea6d060df9ed` |
| `artifacts/f87a_ruleset_qualification/reports.json` | `65718803d3edf2a186b56b1d993b1fae614ae50495b565928e05282ff3e6678f` |

All six controls remain `overall_status=DEFER`, but negative controls now carry Layer-B/C evidence: F86C exposes lattice/rank/residue/sink/one-way/reachability pathology; F86I exposes high local reversibility plus insufficient terminal-template transport; F86N-R1 boundaries expose structural backbone witnesses without admission; Western Chess and Standard Shogi defer semantic movement metrics without heuristic failure. Layer C replay identity passes for legacy controls and is `UNMEASURED` for semantic-only built-ins; playability remains a separate `DEFER` gate.

Budgets were two pairs, two role swaps, four legacy/boundary controls, max 32 plies, zero search nodes, zero Arena games, zero training steps, and zero Heavy jobs. F87B strength ladder, C2, F85, and QD/MAP-Elites remain unauthorized.

Focused verification: `32 passed` across F87A, F86A, F86I, F86M, and F86N tests. Local `HEAD` and `origin/sandbox` both resolve to the checkpoint SHA above before this report commit.
