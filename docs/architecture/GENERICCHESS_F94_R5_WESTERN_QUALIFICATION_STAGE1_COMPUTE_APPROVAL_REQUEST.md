# F94-R5 Western qualification Stage-1 compute approval request

This is a request for Chat scientific approval, not a run authorization. No
Arena or Heavy execution has been started.

Exact immutable bindings:

- sandbox SHA: `03b16b5f6c9b5bcc38575ef811937770e049ac01`
- plan ID: `f94-r5-western-qualification-stage1-20260913-v1`
- plan SHA256: `a1094d869bbc04770780805beff3b193b4370dd373d0647aebcd3cc77ea95738`
- resource-envelope SHA256: `164f96360ce88ba9aa4537356a68fc609597ff972f73eb778ca515bef99b117f`
- PREP byte SHA256: `5b517ae9660928ad983cf8cf49280b35945f1a8fffcfbc87af8f946b93e1370f`
- PREP fingerprint: `a67911ccea9330a5596285ea3dc571e885805864247c25bd8b9ba12284280d31`
- protocol source SHA: `ae70cf306af4bf406491863740506150d872d2a1`
- mechanical compute classification: `large` (`arena_pairs=18 >= 16`)

The exact immutable command argv is:

```text
.venv\Scripts\python.exe -m scripts.f94_r5_western_qualification_stage1_executor --result --prep docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_STAGE1_PREP.json --result-output .generic_chess_flow/f94-r5-western-qualification-stage1-result.json
```

Frozen scientific scope is exactly three invocations over tapes
`9701/9702/9703`, six role-swapped pairs per tape, 18 pairs, 36 games, and
36 action traces; child `4096` versus parent `256` nodes/move, depth `12`, TT
`8 MiB`, workers `1`, and concurrency `1`. The Stage-1-only deterministic
bootstrap is 10,000 resamples with seed `9701001` and 95% percentile CI. All
prior P0/R2/R3/R5 and 9601/9602/9603 observations remain excluded.

Resource bounds are two logical CPUs with one lane, expected wall time 10
minutes and hard wall 20 minutes, expected CPU 2 hours and hard CPU 4 hours,
maximum 180,000,000 nodes and 36,000 plies. The plan has one stage and no
additional games, workers, tuning, Stage 2, full R5, production mutation, or
Layer-D claim.

Explicit request: Chat scientific approval must be bound to this exact plan
SHA, envelope SHA, sandbox SHA, PREP byte SHA, argv, scope, and resource
envelope. If approved, the registered Supervisor must separately review the
same immutable bindings and issue final launch authorization. Until both
approvals exist, the worker must not invoke Heavy.
