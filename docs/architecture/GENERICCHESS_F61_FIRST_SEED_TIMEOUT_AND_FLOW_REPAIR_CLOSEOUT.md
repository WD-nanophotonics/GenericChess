# F61 first-seed timeout and Courier flow repair closeout

Date: 2026-09-13

## Evidence boundary

The approved F61 first-seed run used plan
`f61-gen0-gen1-first-seed-20260913-v1`, envelope
`ade51ba367d9b8cd98d400e21eccb80fd3fa85fceb99912d50614979755a1a23`, and
sandbox checkpoint
`8953f80f4e3abdd5151cada8b339599184369143`. Chat and the registered
Supervisor approved that exact plan, envelope, command, and resource bound.

Heavy run `f61-gen0-gen1-first-seed-44e87ab52d9b` passed launch/preflight and
ran to its declared 45-minute hard wall. It produced no result directory or
stdout/stderr evidence. The registered Supervisor terminated the exact child
process tree at the bound; the recorded state was `failed` with exit code
`4294967295`. The run was not retried or expanded, and no scientific result is
claimed from it.

## Framework repair

This checkpoint separates response transport validity from optional control
fields. Missing or invalid ordinary controls normalize independently to
`CONTINUE`/`NONE`/`HOLD` with warnings; an approval without a valid candidate is
downgraded to `HOLD`. `LOCAL_SUPERVISOR_REQUIRED=true` is imported as a
business escalation, deduplicated by request/response identity, and emits a
stable `NEXT_ACTION=notify registered Supervisor` notice without invoking
transport recovery.

Large compute requests now send the full validated plan and resource envelope
to Chat through `compute-plan-request`; Chat supplies only an explicit
`APPROVE`/`HOLD` decision. The registered Supervisor binds the current normal
response locally to plan, envelope, sandbox, and command identity. The legacy
approval-file path remains strict and supported. Heavy monitoring now enforces
the validated `hard_wall_minutes` bound and records a terminal `timed_out`
state while retaining logs.

## Verification

Passed focused regression suite:

```text
.venv\\Scripts\\python.exe -m pytest tests/test_generic_chess_flow.py tests/test_compute_plan_gate.py -q
94 passed
```

`git diff --check` passed. A broader `pytest -q` run was stopped by the
registered Supervisor after 10m32s under the proportionality rule; it is not
reported as a full-suite pass. No generated heavy output or runtime state is
tracked in this checkpoint.
