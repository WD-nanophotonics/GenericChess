# Incomplete opaque bridge loses imported occurrence

All12 declared cells ran. Four opaque contexts in each original/published arm
hit exactly one occurrence constructor call. Old imported count is removed,
fresh target construction raises MemoryError, and rollback raises
AssertionError("runtime bridge target occurrence is missing") instead of
rethrowing MemoryError. Original MemoryError survives as __context__; it is
not erased. Total occurrence count4 becomes3, including forced-hash and natural
nested cases. Position/ply/terminal, identity/hash, snapshot/history/context,
opaque key set, aliases, frozen parent frame fields and root cache/bindings
restore; actual counts do not.

Natural fixture: a real deterministic3ply cycle retains repetition counts but
imports history=(); from_state legitimately selects opaque history. Nested
fixture starts from real2ply opaque root, performs a successful outer move,
then targets an old imported state. No inconsistent private count table or
manual alias is manufactured. Complete-history same-action controls do not
hit a bridge allocation, succeed publicly and restore after pop.

Ordinary first-child constructor failure propagates MemoryError, preserves
actual count and leaves one empty hash bucket. Bridge collision cases lose the
count even without a distinct new/empty bucket. Therefore empty-container
structure and numeric occurrence loss are distinct, and table-size/hash-bucket
checks cannot stand in for exact identity/count multiplicity.

The one-condition published snapshot rollback repair is valid under its earlier
finite premise; it does not repair this incomplete migration boundary. Source
requires target allocation before destructive migration or an explicit partial
journal, rather than swallowing a missing-target assertion. Primary owns that
choice/integration. A new existing-target merge is outside this constructor
premise, since it does not construct the fresh target at this point.

Dot independently read immutable source and accepted this narrow single-fault
check; it did not execute tests. Its demand for real normal-import inputs,
exact-stage single hit and independent state fields is supported by the local
fixture and records. Receipt-associated advice is not byte-verified Slack
payload or independent execution.

No actual user/UI incident, natural OOM rate, global exhausted-memory recovery,
TT wrong cutoff, timing or generic-domain completeness. Corrupted runtimes are
discarded after diagnostic capture; finite fix acceptance must preserve the
original exception object and exact counts/aliases, then permit ordinary retry.
