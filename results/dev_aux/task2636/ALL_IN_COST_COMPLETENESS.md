# task2636 all-in cost completeness

Frozen design values (do not change): 6,600s lifetime hard cap; stage caps 1,200s preparation/audit/reporting, 2,400s training and 3,000s evaluation. The plan charges 542.632s for prior preparation/audit work, leaving 657.368s in that reserve and 6057.368s future total allowance. Source-bound projection is 2110.568s training + 691.419s evaluation + 1,200s reserve = 4001.988s (66.70 min), with a 110-minute hard cap.

The projection uses task2625 execution measurements on a different four-rule panel and is not a runtime guarantee. It does not yet have measured development/validation costs for the candidate-index training/evaluation runners, partial history/query auditors, stop/deadline tests, write-once registration, or final source-bound analysis. Those are required engineering/preflight work, not evidence that can be absorbed by an unexamined reserve. The current 657.368s reserve is explicitly allocated to remaining replay/audit/reporting; the plan provides no measured margin for the missing adapters.

Decision: preserve the 6,600s/110-minute cap and 120-minute Chat-assessment threshold unchanged. Do not launch or register based on 66.70 minutes alone. First estimate the missing implementation and validation work from bounded receipts; if that work is charged to this study, stop within the existing reserve and hard cap, and report partial evidence rather than extending. Count engineering effort separately in the study's information-per-cost comparison. The run remains below 120 minutes by the current projection, but the all-in scope is not yet closed because adapter work is unpriced.

No experiment started and no cap or frozen input changed.

## Continuation engineering-cost checkpoint — 2026-10-21

The same DEV_AUX session ledger rose from 2,074.554978s to 2,715.371352s
confirmed effective work during this continuation: +640.816374s. This work
implemented and adversarially tested only a source-bound per-slot replay
prototype, reviewed receipt composition, and documented the remaining gates; it
did not implement the candidate-index runner, registration, training or
evaluation. It is Agent engineering/research overhead, not elapsed runtime from
a registered experiment timer (no registration exists).

As a conservative information-per-cost allocation, charging that work against
the remaining 657.367934s preparation/audit/report reserve would leave
16.551560s. That is not enough for whole-result integration, actual-terminal
fixtures, stop-safe writes, final audit or reporting. Therefore the frozen
66.70-minute projection is still not an all-in project estimate, and no
registration/launch is justified. Preserve the existing 1,200/2,400/3,000s
stage allocations, 6,600s lifetime cap, 110-minute hard cap and 120-minute
assessment threshold. Any future cost estimate must separately expose
engineering overhead and actual registered-process time; do not imply this
research time was charged to a nonexistent run timer.

A bounded source-context smoke took31.7ms to read/hash the 6,962,023-byte root
pool and index,34.9ms for first candidate compilation plus one query replay,
and24.0ms median for ten cached one-query replays. It confirms context reuse is
cheap for the tested single root; it does not measure multi-query slots, a full
1,024-slot audit, durable writes, or actual-terminal handling. It does not
justify reclaiming the remaining reserve or change the no-registration decision.
See `results/dev_aux/task2636/replay-context-cost-smoke.json`.
