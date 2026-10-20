# task2636 preflight and run lifecycle review

Question: what states and write-once receipts must exist before task2636 can train or evaluate without starting from the design document, retrying, or evaluating a partial model?

## Required state transitions

| State | Entry requirement | Durable evidence | Allowed next state |
|---|---|---|---|
| FROZEN_READY (current) | Candidate-index, rule hashes, root plan/pool/audit and method pins match; no registered pool/run outputs. | Current source-pin replay; audit PASS; absent `run-v1`. | REGISTERED only after an explicit write-once registration pins the session/chat, branch, exact candidate/rule inputs, initial vector, runner/auditors, root and plan hashes, and all-in caps. |
| REGISTERED | Complete source/identity/stop/cap preflight passes; run path is new. | Write-once registration; no model/game work yet. | TRAINING_STARTED only after a single monotonic deadline begins and a start receipt is written. |
| TRAINING_STARTED | One budget origin; 16 ordered candidate arms and 120 fixed roots per arm; fixed 10-channel seed-1977 vector; global and per-stage limits active. | Started receipt, append-only query/episode logs, arm/model checkpoints, final training result. | TRAINING_AUDIT only after graceful complete or partial closure; on incomplete training evaluation is prohibited. |
| TRAINING_PARTIAL / STOPPED_USER / TIME_CAP | Graceful stop or cap; current arm/episode closed when possible with exact counts/weights, UNKNOWN kept distinct from terminal. | Final partial result and independently replayable durable prefix. | TERMINAL_REPORT only; all 1,024 evaluation slots stay missing. |
| NO_FINAL_RECEIPT | Hard interruption before final status. | Original start receipt, raw complete-line prefix, preserved truncated suffix evidence. | READ_ONLY_RECOVERY only; no resume, retry, top-up or evaluation. |
| TRAINING_COMPLETE + AUDIT_PASS | All 16 arms meet the frozen per-candidate 250k combined-node cap and full-history replay passes. | Training result and audit hashes bound together. | EVALUATION_BOUND once, before the first slot. |
| EVALUATION_STARTED | Complete audited training endpoint set; 1,024 pre-enumerated slots and 512 pairs; paired endpoint/color caps frozen; one shared deadline. | Evaluation start, query/slot records, slot closure receipts. | EVALUATION_AUDIT only after full or graceful partial closure. |
| EVALUATION_PARTIAL / STOPPED_USER / TIME_CAP | Stop or cap during panel. | Completed slots and explicit missing slot keys; UNKNOWN and missing separately counted. | BOUNDED_ANALYSIS over the full 512-pair denominator. |
| AUDITED_RESULT | Independent replay of exact source-bound durable rows passes. | Frozen final report with known W/L/D, completed UNKNOWN and missing counts, and completion bounds. | Complete segment checkpoint/publication after content and secret review. |

## Boundary checks

The existing task2625 `bind_evaluation.py` confirms the intended safe gate: it refuses to bind unless the training result is `COMPLETE`, all expected arms exist, the independent training audit passes, and the audit hash matches that result. The task2636 version needs equivalent candidate-index-aware checks. A partial or missing training result leaves evaluation unstarted and all planned evaluation slots missing.

The global 6,600-second cap includes future validation, training, evaluation, audits and reporting; the previously completed prep/audit charge is 542.632 seconds, leaving 6,057.368 seconds. Start one monotonic origin at registration/preflight and never reset it across phases. The estimated run remains under the user’s 120-minute review threshold, but this is a projection, not a runtime guarantee.

Stop handling must cover every poll, not only AlphaBeta's callback. A stop before a query/slot starts does not create that row; an already-started unscored episode/slot closes UNKNOWN only when a durable closure can be written. A hard kill with no final receipt remains `NO_FINAL_RECEIPT`; it never resumes. All missing evaluation endpoints remain in their original 512-pair strata and are not draws.

This is a review checklist, not a registration or implementation. The write-once registration, runner, partial auditors and analyzer do not yet exist. No run, training or evaluation was started.
