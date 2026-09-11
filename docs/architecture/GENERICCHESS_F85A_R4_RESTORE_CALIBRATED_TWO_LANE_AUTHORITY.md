# GenericChess F85A-R4 Restore Calibrated Two-Lane Authority

F85A-R4 restores the accepted F85A-R2 runtime authority after review of the
R3 smoke diagnostic. This is a zero-compute corrective: no Heavy run, F59
teacher call, 36-root acquisition, C2 fit, Arena, root resampling, manifest
change, or production semantic change was performed.

## Restored authority

`MAX_CONCURRENT_ROOTS` is restored to `2`, matching the frozen manifest's
`execution_contract.max_concurrent_roots == 2`. `_validate_execution_plan()`
accepts only `intended_cpu_lanes == 2`; `_run_approved_acquisition()` rejects
non-two-lane direct calls and uses the validated value as its batch width.
Contract tests cover a passing two-lane plan and rejection of both three- and
four-lane plans before any teacher runner can start.

The frozen manifest remains unchanged, including its Git blob
`f0afca1fc1979a692a841f3fcb25da10a8e6d482`, 36 train roots, 12/12/12 strata,
and total declared node ceiling `15,426,000`.

## R3 diagnostic disposition

The R3 smoke probe remains as diagnostic history only. It used the three F84
resource roots and 50/100/200-node smoke budgets, not the full F59 teacher
contract. Its results therefore cannot establish full-workload memory scaling
or supersede F84's full-contract two-lane calibration. No further lane
experiment is authorized by this corrective.

## Classification

`C2_TRAIN_TEACHER_ACQUISITION_HARNESS_READY_FOR_LARGE_APPROVAL`

The next and only execution step is a separately approved exact two-lane large
compute tuple: 16 logical CPUs, one stage, 720-second per-root cap, 110-minute
expected wall, 95–125-minute planning range, 240-minute hard wall, 8.5
expected CPU-hours, 15 hard CPU-hours, and zero effective games/pairs/plies.
