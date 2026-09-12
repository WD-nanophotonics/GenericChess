# F94-R4 censor semantics and Western tail audit

The Layer-D ceiling fraction now counts only `engine_role="child"`, the
strong-budget side, rather than recursively mixing 256-node parent and
4096-node child metrics. Raw per-search depth hits remain evidence; the repair
only makes the aggregate fraction describe the named budget side.

The cached R3 Western games reached `max_ply` because Western Chess is compiled
with `max_ply=1000` and `repetition_limit=100000`; terminal evaluation checks
repetition before max-ply, so the recorded `max_ply` results establish the
configured horizon was reached and do not establish repetition. Four of six
games ended at 995--997 post-opening plies. R3 result records metrics but not
action histories, so a deterministic replay witness cannot be reconstructed
without a new, separately frozen protocol; no Arena was rerun.

R3 remains non-authoritative and non-poolable. Any future PREP must preserve
raw role-aware telemetry and separately decide how to treat sparse depth hits
and the Western horizon before collecting new samples.
