# Agent execution policy

# Agent single-run execution policy v2

For the active inbox TASK, run `gc-bridge ensure` and `gc-bridge sync`, read the
latest TASK/AUDIT, and execute the complete authorized scope in one run.
Commits, pushes, passing tests, phase boundaries, and audits are mechanical
persistence only; they are not stop conditions or reasons to return progress.
Stop only at COMPLETE or after a genuine HARD_BLOCKED condition is demonstrated
and safe local recovery is exhausted. This policy supersedes v1.
