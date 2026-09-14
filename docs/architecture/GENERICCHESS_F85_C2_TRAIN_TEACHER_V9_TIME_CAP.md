# GenericChess F85 C2 teacher acquisition v9 time-cap closeout

Status: `C2_TRAIN_TEACHER_EVIDENCE_INCOMPLETE_TIME_CAP`.

The cap-only continuation was approved by Chat and the registered Supervisor
at sandbox `51e1efaaa489c888f61396faa08ca4f3ffe9b352`. The exact plan digest
was `a47b25130778eb72036860d37ae1c7fcd2aaf16f04c24205aff3712bd80f91c0` and
the resource-envelope digest was
`7b69e98c65b33cdf284d227726313dbb299fc98c64d06dbac607d5208f722281`.
The F85 manifest remained unchanged at
`8c026d5fb33ee3b1da60f2fd10ad417ac3c7126f948ed64bc2d94e6e38eee8f6`.

Heavy run `f85-c2-train-teacher-v9-9343eb615cc1` changed only the per-root
wall allowance to 1,800 seconds and the stage hard wall to 10 hours. The same
two first roots (`reachable_random-a-00` and `reachable_random-a-01`) both
reached `per_root_wall_cap`; the harness returned
`INCOMPLETE`/`TERMINAL_ROOT_REQUIRES_NEW_AUTHORIZATION`, completed count `0/36`,
and emitted no `training_evidence.json`.

The v8 TIME_CAP records remain historical and were not reused. No further cap
increase, root substitution, C2 fitting, or Arena execution is authorized by
this closeout; a continuation requires a new scientific route and explicit
Supervisor decision.
