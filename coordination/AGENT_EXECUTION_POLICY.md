# Agent execution policy

For the active inbox TASK, run `gc-bridge ensure` and `gc-bridge sync`, read the
latest TASK/AUDIT, then continue implementation through all authorized phases.
Commits, pushes, passing tests, phase boundaries, and pending audits are not
stop conditions. Stop only when the task is complete or a genuine hard blocker
has been demonstrated and safe local recovery is exhausted.
