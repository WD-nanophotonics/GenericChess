# GenericChess F81-R2: corrective rerun compute gate

Status: `COMPUTE_APPROVAL_REQUIRED`.

The zero-compute audit and minimal Arena cap-contract fix are complete. No F81
R2 corrective Arena game has been launched.

The audit at
`artifacts/f81_final_confirmation/f81_r1_time_cap_audit.json` validated all 16
old game files and found exactly one contaminated pair: original pair index
`5`. Its audit content SHA is
`1c418b509654f4f054db738720880bf4435e611bd2cba589b4018d78a2c961a6`.
The contaminated pair's trusted elapsed totals are:

- owner 0: `2686.2614457980017` seconds;
- owner 1: `612.134558499` seconds.

The required corrective schedule has two lanes. The owner-0 measured workload
alone therefore establishes a wall-time lower bound of about 44.77 minutes;
the required small/medium estimate of at most 30 minutes is not credible. Work
stops here under the order's compute rule.

The versioned large-compute plan is
`.generic_chess_flow/compute-plans/f81-r2-time-budget-corrective-v1.json` with
plan SHA to be bound to the current checkpoint after this report is published;
its envelope is
`.generic_chess_flow/f81-r2-time-budget-corrective-envelope-v1.json`. The
planned envelope declares 50 expected wall minutes (45–55 range), 60 hard wall
minutes, two lanes, one pair, two games, and the unchanged 3,600-second,
262,144-node, and 512-ply caps.

Execution remains blocked until Chat scientific approval and registered-
Supervisor approval are bound to the exact plan SHA, envelope digest, and
current sandbox SHA. If approved, only original pair 5 may be rerun in the
fresh `f81-r2-time-budget-corrective` namespace; no clean pair may be rerun and
no old/new game mixing is allowed.
