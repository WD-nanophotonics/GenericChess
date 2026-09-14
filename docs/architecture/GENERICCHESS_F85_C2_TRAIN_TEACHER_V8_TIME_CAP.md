# GenericChess F85 C2 teacher acquisition v8 time-cap closeout

Status: `C2_TRAIN_TEACHER_EVIDENCE_INCOMPLETE_TIME_CAP`.

The exact Chat- and Supervisor-approved plan
`f85-c2-train-teacher-acquisition-v8` ran at sandbox
`cfbbc19368c1ef71af4518b3ac24a91897e2c728`, plan digest
`edcc5dffe2c63a7ec1847cc73b5f27ce3e254bcd73d81346dfb8e7a95ac003df`, and
resource-envelope digest
`ede57d4bf8d6a512625fde262a85f1a5eaa144599a55abf62d464bf90be69fa3`.
The immutable F85 precompute manifest was
`8c026d5fb33ee3b1da60f2fd10ad417ac3c7126f948ed64bc2d94e6e38eee8f6`.

Heavy run `f85-c2-train-teacher-v8-82f769ff0b69` launched only the approved
36-root teacher acquisition (two root lanes, no candidate fit and no Arena).
The first batch, `reachable_random-a-00` and `reachable_random-a-01`, both
reached the registered 720-second per-root cap. The harness wrote two atomic
`TIME_CAP` progress records, completed count `0/36`, returned
`INCOMPLETE`/`TERMINAL_ROOT_REQUIRES_NEW_AUTHORIZATION`, and did not create
`training_evidence.json` for this plan.

No retry, wall-cap increase, root substitution, C2 fitting, or Arena work is
authorized by this closeout. Any continuation requires a new explicit Chat
plan and a new Supervisor decision; the current C2 candidate remains
unformed.
