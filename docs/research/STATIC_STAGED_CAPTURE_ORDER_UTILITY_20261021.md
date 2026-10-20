# Staged capture-order utility on generated rules — 2026-10-21

## Question and frozen contrast

Does static-v2 capture_order_value on the opt-in Python StagedMovePicker path merit a scoped candidate when leaf evaluation and opponent remain fixed? The 64-slot frozen plan changes only the capture-order hook. Both arms use staged search, Unit leaf values, identical Unit foe, D3/8192 nodes/0.5-second search/q0, TT off, new generated 5x5 rule seeds 622091–622098, both candidate owners, and 3/4-ply roots. Expected runtime was 600 seconds with a 3600-second cap; actual runtime was 222.656 seconds. No defaults or product code changed.

The separate default MoveOrderer capture screen is reported in STATIC_CAPTURE_ORDER_UTILITY_20261021.md; this is the distinct optional staged mechanism proposed in the incoming Chat comments.

## Results

All 64 slots returned: 55 actual terminals, 9 retained UNKNOWNs, no invalid actions, replay mismatches, or unstarted slots. The preflight altered 11/16 root capture orders and 7 fixed-leaf root choices; in the utility panel first candidate actions differed on 12/32 comparable paired states.

Static-minus-Unit finite reward bounds were [-0.500,+0.0625] overall, [-0.5625,-0.0625] for owner 0, and [-0.4375,+0.1875] for owner 1. The predeclared utility and cost gates both failed. Median paired candidate-node reduction was -0.277% overall, -3.84% for owner 0, and 0% for owner 1; the aggregate is not evidence of a robust improvement. Observed W/L/U was 9/16/7 for static and 12/12/4 for Unit. These are descriptive finite-panel counts, not a population win-rate estimate.

## Decision and scope

Do not retain static-v2 capture ordering on the staged path and do not change defaults. This closes only the tested 5x5 generated-rule sample and budgets. It does not refute static leaf values, promotion-target ordering, other search budgets, or all generated rules. Do not rerun or select seeds/owners after observing results.

## Reproducibility

Plan, preflight, producer, analyzer, full games and independent audit are in data/static_staged_capture_order_utility_20261021/. The independent audit regenerated 8 rules and profiles and replayed all 64 complete histories; it found 16 roots, zero invalid actions and zero producer replay-mismatch flags. The panel is bound to source HEAD e009c4a531aebd21bf8d07cb2115b43786cc3d94; focused picker tests passed 11/11 before this utility run.
