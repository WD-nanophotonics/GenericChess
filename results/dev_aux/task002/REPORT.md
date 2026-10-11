# Task002 independent cancellation and attribution audit

DEV_AUX; pinned product baseline b4108a68a7ee06327be39cb3a222939644085a52.
No product or original producer edits. Original physical producer SHA256:
99a317ec4d3456b2748df8738080ba86e7d78abfcbd9697a002dcee2508b1ed5.

36 completed calls preserve plain/instrumented public decisions and full
non-time internal SearchStatistics:16 fixed-observation cancellations,
16 phase-targeted cancellations and4 attempt-complete diagnostic calls.
Both orders are included. All controls preserve Session position/history,
balanced runtime push/pop and empty probe frame/pending stacks.
This is one exposed Chess-middle case and one fixed evaluator/q configuration;
it establishes neither all-rule correctness nor a speed improvement.

## Concrete findings

The original probe classifies successful formal children only. Its exception
path discards the failed attempt's local selected-stage Counter. The fixed
32/128/512/2048 observation controls report0/1/4/19 children despite
1/2/5/20 attempts. This is a cost-reporting boundary, not an observed state
restoration defect.

Root/main1/main2/q cancellation reaches attempts1/36/71/73 respectively.
The last two return completedD1. The qphase control already contains two
successful formal pushes from ultimately aborted iteration2, plus one failed
attempt. Counting only the last failed push does not describe all work in an
unfinished iteration. Successful work is not automatically wasted: possible
TT reuse is outside this audit.

The separate diagnostic sets cancellation after the first iteration2 qphase
transition returns. Each call retains35 successful root-scan children,
35 successful children in completed iteration1, two successful children in
aborted iteration2 and one failed attempt. The original measured probe counts
72 successful children. The failed attempt additionally executes one selected
runtime-frontier, transition and attack call, all absent from original
per-child totals. Independent selected-method entry counts equal successful
classified calls plus failed-attempt calls plus outside calls.

Existing formal-child iteration IDs, joined with final completed_depth, suffice
to distinguish completed versus aborted work in this driver. Thus the narrow
hypothesis that Root/Main/q child categories must be redesigned is rejected:
retain categories and add the final-disposition join. However, the original
outside_formal_push Counter aggregates iterations/phases, so it cannot supply
that join for outside work. If using full cost attribution for a completion
change, retain failed-attempt values and phase/iteration-tag outside work too.

Nested inclusive durations must never be added as exclusive totals. Exclusive
means only selected nested seams removed, not all Python work. Diagnostic
seconds are descriptive, not an estimate of optimization gains or controlled
timing; no bilateral CPU lock has been adopted.

## Review and limitations

Dot's suggestion to separate successful-child status from final iteration
completion was adopted, then tested independently. The original formal-child
schema already permits the join; outside aggregation remains a distinct limit.
Raw consultation records remain ignored and are not published.

The first attempt-ledger adapter incorrectly used the measured-only probe stack
to label independent method entries in both arms. Its pair assertion failed.
The corrected adapter observes its own current attempt equally in both arms;
no cancellation target, limits or product source changed. The development
failure is retained in ledger_development_failure.json, and the four completed
controls are diagnostic evidence rather than independent holdout.

Reproduce with the three *_audit.py files using the own runtime and archived
producer set verified in Task001. cancellation.json, phase_cancellation.json
and attempt_ledger.json contain full non-time statistics and original stages.
Declaration bounds were fixed before each distinct mechanism check. Cancellation
flags on a selected seam differ from natural wall-time aborts; no frequency
or real-time benefit is inferred. Product counters for completed pushes are
not asserted to count failed attempts. No q/evaluator/UI/default changes.
