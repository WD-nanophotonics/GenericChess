# F94 R7 compute-plan boundary closeout

This is a plan-only, result-free checkpoint. No Heavy, Arena, native
compilation, or R7 tape was started.

## Published plan boundary

- Plan request checkpoint: `3b968913b265d01e7b9bcc67fc690d81b0c1abe0`
- Runtime plan: `.generic_chess_flow/compute-plans/f94-r7-layer-d-authority-20260913-v1.json`
- Runtime envelope: `.generic_chess_flow/compute-plans/f94-r7-layer-d-authority-20260913-envelope-v1.json`
- Workload: two controls × three fresh tapes × three matchups × six pairs × two games = 216 games.
- Fresh tapes: `9811`, `9812`, `9813`; excluded R6 tapes: `9801`, `9802`, `9803`.
- Primary endpoint: `4096_vs_256`; diagnostics: `1024_vs_256`, `4096_vs_1024`.

The plan declares four bounded lanes, 20 logical CPUs, 35 expected / 120 hard
wall minutes, 12 expected / 24 hard CPU-hours, 800,000,000 maximum nodes, and
163,296 maximum plies. It is classified `large` by the flow policy. The
runtime plan and envelope are rebound to the final closeout SHA after this
report-only commit, then `compute-plan-status` is rerun read-only; no approval
is present.

## Approval boundary

Before any future `heavy` invocation, Chat scientific approval and registered
Supervisor approval must independently bind the exact current sandbox SHA,
plan SHA, envelope digest, and command argv. Smaller, partial, or primary-only
runs are not valid substitutes. The R7 endpoint rule remains prospective and
R6 `DEFER_CONTROL_NOT_READY` remains immutable.
