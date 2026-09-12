# F94-R5 staged approval proposal

Status: approval request only. No R5 RESULT, Stage 0, Stage 1, Arena, or
Heavy computation has been launched.

## Decision requested

Approve the following sequential protocol against this published report:

1. Stage 0 runs only the two READY candidates (Built-in Western Chess and
   Built-in Standard Shogi), on the three frozen R5 tapes, with one
   role-swapped 4096-node versus 256-node pair per tape. This is six
   single-worker Arena invocations and twelve games total. The frozen boundary
   candidate remains an A/C prerequisite short circuit with zero compute.
2. Stop after Stage 0 if either candidate is clearly negative, any fallback,
   depth-censoring, cap, or operational failure invalidates the response, or
   measured runtime makes expansion unjustified. These are unresolved findings,
   not PASS or draw results.
3. Only if both candidates are positive on all three tapes, uncensored,
   reproducible, and still economically reasonable, request a separately
   approved Stage 1 of 18 pairs and 36 games total, using the same frozen tapes
   and identities. Stage 1 is not authorized by this report.
4. Only if Stage 1 remains positive, uncensored, reproducible, and
   precision-relevant should a new current-SHA review reopen the full R5
   contract. The 216-game RESULT is not authorized by this proposal.

The scientific contract remains frozen: workers=1, depth 12, 8 MiB TT, the
256/1024/4096 ladder, the three tapes, the candidate identities, and the
boundary short circuit are unchanged. No outer parallelism, tuning, training,
ruleset change, or promotion is included.

## Necessity and cost

The completed R2 Stage-0 and R3 calibrations each used six single-worker
invocations and twelve games, with an expected envelope of about 30 wall
minutes and 1.5 CPU-hours. They are descriptive and non-authoritative:

| Evidence | Western Chess | Standard Shogi | Consequence |
| --- | --- | --- | --- |
| R2 Stage-0 | depth-censored on all tapes; pooled effect 0.1667, CI [0.00, 0.25] | positive direction on all tapes; pooled effect 0.4167, CI [0.25, 0.50] | cannot pass Layer D or justify expansion |
| R3 depth-64 | depth-censored on two tapes; pooled effect 0.1667, CI [0.00, 0.25] | positive direction on all tapes; pooled effect 0.4167, CI [0.25, 0.50] | removes the R2 depth-12 confound but remains descriptive |

The frozen full R5 contract would require 18 invocations, 108 paired scores,
216 games, 216 action traces, and 72 strongest-vs-weakest horizon games. Its
current approval-only estimate is approximately 720 wall minutes and 12
CPU-hours at one lane, about eighteen times the twelve-game Stage-0 game
count. Running that schedule before a cheap directional/censoring decision
would spend the large budget without resolving the present uncertainty.

Stage 0 is therefore the cheapest sufficient next decision procedure. Its
sequential stop rule can avoid all further compute when the response is
negative, censored, operationally invalid, or too costly. Stage 1 is capped at
36 games and is considered only after Stage-0 evidence is positive,
uncensored, reproducible, and economically reasonable. Existing R2/R3 samples
are not pooled into R5 and cannot substitute for these gates.

## Immutable evidence

- Current published sandbox checkpoint before this report: `04e32e8707d2a2839c9f6609001cad12be3ef493`.
- `docs/architecture/GENERICCHESS_F94_R2_STAGE0_RUNTIME_CLOSEOUT.md`.
- `docs/architecture/GENERICCHESS_F94_R3_NONBINDING_DEPTH_CALIBRATION_RUNTIME_CLOSEOUT.md`.
- `docs/architecture/GENERICCHESS_F94_R2_STAGED_CALIBRATION_PLAN.md`.
- `docs/architecture/GENERICCHESS_F94_R5_R1_HORIZON_AWARE_PREP_CLOSEOUT.md`.
- `docs/architecture/GENERICCHESS_F94_R5_R2_R1_PROVENANCE_ACCOUNTING_CLOSEOUT.md`.

## Approval boundary

This report asks Chat for exact scientific approval of the staged protocol
only. After Chat returns its control fields and approval, a fresh current-SHA
Stage-0 resource envelope and versioned compute plan will be generated and
sent to the registered Supervisor for binding to the exact sandbox SHA,
envelope digest, plan SHA, and command argv. No Heavy command may start before
both approvals are bound. If Chat revises the stage or stop rule, that revision
supersedes this proposal before any plan is generated.
