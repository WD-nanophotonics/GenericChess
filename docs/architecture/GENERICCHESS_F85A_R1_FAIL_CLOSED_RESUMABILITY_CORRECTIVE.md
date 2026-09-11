# GenericChess F85A-R1 Fail-Closed Resumability Corrective

This corrective keeps the F85A 36-root manifest, root identities, legal counts,
node ceilings, C1 identity, F84 SHA, and F59/F62 teacher contract unchanged.
It performs zero teacher compute, no Heavy acquisition, no C2 fitting, no Arena,
and no root resampling.

## Corrective guarantees

- Runtime progress is namespaced by the exact compute-plan SHA.
- Every COMPLETE unit binds the plan SHA, manifest content SHA, exact root-record
  SHA, root identity, role/stratum, C1 checkpoint/model, and F59/F62 source SHAs.
  A stale COMPLETE unit is a harness mismatch and is never reused.
- TIME_CAP and HARNESS_MISMATCH units persist status/provenance but never teacher
  rows. Re-entering the same plan with a terminal unit returns
  `RETRY_REQUIRES_NEW_AUTHORIZATION` without invoking teacher code.
- Scheduling is deterministic and bounded: at most the approved lane count is
  submitted, each batch completes before the next batch is submitted, and any
  terminal result stops later batches. A sibling already in the same batch may
  finish and be persisted; no later batch is started.
- `training_evidence.json` is created only after exact, provenance-bound 36/36
  COMPLETE units exist.

## F84 lane tradeoff for the next approval tuple

F84 measured per-root wall/process CPU of approximately 331/685, 399/948, and
265/607 seconds. The observed process CPU/wall ratios are about 2.1–2.4 logical
cores per root. Using F84’s balanced train-only projection as the baseline:

| Root lanes | Balanced wall projection | CPU projection | Risk posture |
| --- | ---: | ---: | --- |
| 2 | ~99.6 min | ~7.5 CPU-h | calibrated geometry; lowest interference risk |
| 3 | ~66.4 min | ~7.5 CPU-h | unmeasured lane scaling; moderate interference risk |
| 4 | ~49.8 min | ~7.5 CPU-h | ~8–10 logical cores implied by F84 CPU use; within 16 declared CPUs, but RSS was not measured |

F84 provides no evidence that four lanes are unsafe on the 16-logical-CPU host;
the main unmeasured risk is memory/interference, not CPU oversubscription. The
next runtime envelope therefore uses four intended root lanes, with expected
wall 55 minutes, a 45–63 minute range, hard wall 180 minutes, expected CPU
8.5 hours, and hard CPU 15 hours. Effective games, Arena pairs, and plies
remain zero. This is only a plan revision; no acquisition is authorized by this
corrective.

## Verification

The fake-worker suite covers 36/36 sealing, terminal first-batch stop, same-plan
terminal non-retry, and stale COMPLETE rejection. The existing F82/F83/F84
contract suites remain required. The manifest remains unchanged.
