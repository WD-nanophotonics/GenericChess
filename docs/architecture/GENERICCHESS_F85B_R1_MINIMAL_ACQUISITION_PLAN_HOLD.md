# GenericChess F85B-R1 minimal acquisition execution repair

Status: `C2_MINIMAL_TEACHER_ROWS_PLAN_HOLD`.

The phase-resumable minimal acquisition repairs are published at sandbox
`e20d6372c693988e4678305a7700f712f350d43b`. The runner now uses the approved
plan's positive `per_root_wall_seconds`, executes at most two terminable root
workers, reuses only provenance-identical COMPLETE phases, seals every root
with root/role/stratum identity, accounts searches as `2 + L + S`, and writes
the canonical F82-consumed `artifacts/f85_c2_train_teacher_evidence/training_evidence.json`.
The focused suite passed 26 tests, including F59 equivalence, phase resume,
TIME_CAP behavior, and canonical evidence consumption.

The fresh v11 minimal-acquisition plan is bound to this checkpoint and minimal
manifest SHA `585550922d28ca7c17dd5431c98409b8750653933722661f2cc9cdf7a7e5d37b`.
Chat returned `GENERICCHESS_COMPUTE_PLAN_APPROVAL=HOLD`; plan SHA is
`fc419f10b8747dc5ef59eddb679ea2e6ada329f80a48f9207f708e8db609ca95` and
envelope SHA is `4f4ece8880077b0921ad3de8a2a2500be88b05ed7b99184b6f05f3b6520fe63e`.
No Heavy, C2 fitting, or Arena work was launched.
