# GenericChess F85A C2 Train Teacher Acquisition Harness and Large Plan

F85A prepares the next large-compute approval tuple without executing teacher
acquisition. The harness is resumable at per-root units, but acquisition is
withheld until the workflow validates an exact approved plan; `--precompute-only`
is the only mode used in this work order. No teacher path, C2 fitting,
candidate generation, Arena, or Heavy acquisition is run here.

## Frozen work set

The precompute manifest binds the F83 root-set identity
`c197799729877dc836116740d0827de0b02cfabde42e45c8e53e19f61c3ee108` and
selects exactly 36 `role == train` roots: 12 each from reachable-random,
C1-on-policy, and C1-PV-corridor. Dev and resource roots are excluded.
Each root is replay-validated, its legal-action count is recorded, and the
maximum selected-action count is fixed at 9.

The exact teacher contract is F59/F62: C1 parent and observer, root budgets
2k/40k/80k, observer 2k, all-legal child budget 1k, selected child budgets
10k/20k, depth 12, 8 MiB TT, and root-window pruning disabled. Per-root and
total declared node ceilings are recorded in
`artifacts/f85_c2_train_teacher_evidence/train_precompute_manifest.json`.

## Large-compute tuple preparation

F84 measured enough to establish that 36-root acquisition is large work. The
planned envelope retains two root lanes and 16 logical CPUs, one stage, a
720-second per-root cap, an expected wall range of 95–125 minutes (baseline
110), a 240-minute hard wall, expected CPU 8.5 hours, and hard CPU 15 hours.
Effective games, Arena pairs, and plies are all zero. The compute plan and
envelope are generated only after the final published checkpoint, remain in
ignored runtime state, and must be approved against that exact checkpoint,
manifest SHA, command, and envelope digest before any acquisition runs.
