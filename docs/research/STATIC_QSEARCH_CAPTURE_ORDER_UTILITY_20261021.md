# Quiescence-search capture-order utility - 2026-10-21

## Question and frozen contrast

Does static-v2 capture-order scoring improve finite search outcomes when the only changed consumer is capture ordering inside Python AlphaBeta quiescence search? The fixed 64-game panel used eight newly generated 5x5 rule seeds (622101-622108), two roots per seed at 3 and 4 plies, both candidate owners, D3/8192 nodes/0.5 seconds/q2/qhard2/qnodes128, TT off, Unit main-search leaves, Unit opponent, and ordinary Unit ordering. Only the qsearch capture-order hook differed. The producer used a scoped wrapper that restored the Unit evaluator before recursive search; this kept the main-search ordering/leaf path fixed. Source and wrapper isolation were preflighted before collecting outcomes.

The run completed in 66.0 seconds (58.394 seconds caller time), below the 3600-second per-run cap. Focused correctness/scope tests passed: 20 tests. No product code or defaults changed.

## Results

All 64 slots returned: 48 terminals and 16 HORIZON_48_CANDIDATE_UNKNOWN; no unstarted slots, invalid actions, or history replay mismatches. Candidate W/D/L/UNKNOWN counts were Unit 8/8/8/8 and static-v2 7/8/9/8 over 32 games per arm. Conservative paired utility for static-v2 minus Unit was [-0.5625,+0.4375] overall, [-0.625,+0.375] for owner 0 and [-0.500,+0.500] for owner 1. Candidate-first/reply bounds were [-0.500,+0.500] and [-0.625,+0.375]; all leave-one-seed-out lower bounds were negative (minimum -0.6429).

The predeclared utility and cost retention gates both failed. Median paired candidate-node reduction was zero overall and in each owner/root-ply stratum; aggregate candidate nodes were 71,653 for static-v2 versus 71,634 for Unit. Caller time was 15.130 versus 14.630 seconds. Static-v2 produced 4,827 qsearch capture-order values outside the normal Unit value domain, yet only 2 of 692 common candidate states changed action. This confirms the hook was exercised while showing little decision exposure in this sample; it does not establish utility.

## Decision and scope

Close this qsearch capture-order candidate for the tested 5x5 generated-rule domain and budget. Do not repeat/widen the panel, promote the value into defaults, or infer a general ordering or strength law. This result does not test qsearch leaf evaluation. A separate one-root feasibility probe shows that changing only qsearch stand-pat leaf values can alter the selected root action while main-search leaf calls and ordering remain Unit; this supports a distinct, separately frozen utility question, not an efficacy claim.

## Reproducibility and limits

Plan SHA-256 4add564a50f25460cdaca097f816889908643944d5a50f6045d9677ab8854069; preflight SHA-256 820a5e36c9795699449cd919b884e041018b212ea3afcf11d4c3477d4b4f0f4d; producer SHA-256 ff339db5680db0f060b12ee4eacbdfbe03dbaa6f2eb74fed2f5065f7f7284136; analysis is bound to those files and execution SHA a8e2b88ad6240f0d79a4d1dbeaebcfb5ce2691124fafd667adaed8b293c64292. Full per-game rows, root/rule/profile snapshots, receipts, and independent analysis are in data/static_qsearch_capture_order_utility_20261021/. The paired finite sample retains UNKNOWN rather than imputing outcomes. Candidate nodes are descriptive cost under this fixed cap; they are not a global runtime guarantee.

The distinct qsearch leaf-price one-root preflight uses seed 622109, a generated 5x5 classic-like bilateral rule, and the first three lexical-seeded legal plies. Both arms made 10 main-search evaluations; qsearch stand-pat calls were 84 Unit versus 54 static-v2, and selected actions differed. It collected no outcomes and submitted no action. Its stored root-state SHA-256 is 0a1744c8106d4f0fc357773286fde66bd6bd6be18d77cfad132bbdc17b7704bd. This single feasibility witness is not a utility result.
