# Frozen working target-first constructor acceptance

Eight new candidate-only controls pass. Working Runtime SHA256
39f7592ac788f449213f844dffebdcf100f5a940f20fc7473aa1c6f16f33426f changes
only _resolve_opaque_history_key AST relative to published558b497. Frozen
resolve SHA256cb0f5cd0ef5b5621b1e89c5b4c2b653a7444de64d8238e135b704b8d25a5b922.

Four opaque/nested ordinary/forced-hash cells throw exactly one constructor
fault at the changed pre-journal site. Exact original MemoryError object
escapes with no replacement/context/cause; all frozen root/count/bucket/alias/
parent-frame/cache/history fields restore. Snapshot items/digest agree with
rebuilt actual counts after failure and successful same-Runtime retry. Retry/pop
matches public Core and restores original state. Complete2 controls hit0 and
restore; ordinary2 allocation controls preserve counts, with the original
noncollision empty-bucket limitation explicitly retained.

This independently accepts the narrow target-constructor mechanism. It is a
working-file observation, not immutable publication or primary regression
execution. Task016 separately examines successful target preparation followed
by allocation-capable old-entry comparison: constructor acceptance does not
cover every later migration operation.

Initial copied AST namespace retained the original constructor; the first
opaque expected-hit assertion correctly rejected this ineffective injection.
Two complete controls had run before setup failure. Both failed source and
reason remain; the exact constructor now binds in module and copied namespace,
without source/condition/cap change. This is not a scientific candidate failure.
