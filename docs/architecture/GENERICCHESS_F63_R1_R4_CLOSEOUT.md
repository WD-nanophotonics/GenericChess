# F63-R1-R4 resume-control corrective closeout

Status: corrective implementation complete; no teacher or candidate Heavy was
run.

Parent checkpoint: `2958f61ba46aeab7e0712c8a675fecb744e737ec`

This corrective makes selected-8 continuation decision-aware. `PASS_LOCKED`
continues to the 32-pair confirmation even when the selected-8 execution is a
valid decision-only partial stage; `FAIL_LOCKED` stops as a scientific
negative; unresolved pause/cap/incomplete stages remain explicitly resumable
and cannot be relabeled as replacement-distillation failure. A completed
selected-8 stage with an unresolved criterion continues to the confirmation
stage. A selected-32 stage is positive only when complete and its actual
pair-level bootstrap lower bound is above 0.5; any operationally incomplete
selected-32 stage is explicitly resumable/inconclusive.

The preserved teacher pair-v1 artifact now also validates requested telemetry
before it can authorize the resume branch. Game-v1 persistence, hard search
deadlines, exact-once aggregation, fixed scientific constants, F62 reuse, and
the fail-closed resume boundary are unchanged.

Bounded focused tests passed 41 tests across the F63 harness, game-v1 Arena,
legacy Arena integrity, and self-play Arena suites. The real local teacher
artifact validation passed with `PASS_LOCKED` and seven validated pairs.

The runtime resource envelope and compute plan must be regenerated only after
this final repository checkpoint is published, bound to its exact SHA, and
validated as large with no approval. Candidate Heavy remains prohibited until
Chat and the registered Supervisor approve that exact plan.
