# Task016: allocation-capable equality before old-entry removal

Changed premise after Task015: target preparation succeeds, then old_bucket.remove
compares an earlier _Occurrence before reaching the old imported entry.
Generated dataclass equality constructs tuples; a one-off comparison MemoryError
can occur before list.remove mutates its list, after the new candidate has already
installed target/journal. Does rollback know whether old removal actually happened?

Four cells: immutable published558b497 resolve versus Task015 frozen working
resolve; no fault/single equality fault. Real3ply cycle imported history=(),
with exactly the same public repetition mapping reordered to put child external
key last. Forced RuntimeHash(0,0) makes distinct exact identities share a bucket.
This is a valid order-equivalent imported mapping, not fabricated private counts.
No other game, target or cap extension; this changes the failed operation.

Inject exactly once in original _Occurrence.__eq__ only when immediate Python
caller is _resolve_opaque_history_key, other is target old _ImportedIdentity,
and self is a different bucket entry. Otherwise call original comparator.
Freeze its disassembly evidence for tuple allocation. Control must reach
comparison, complete/public parity and restore after pop. Fault records actual
count multiset, old key count, top/context exception and snapshot versus actual.
Use published push in both arms. No retry of damaged runtime, no product writes.

A failure limits full transaction exception safety; it does not withdraw
Task015's proved constructor-failure acceptance or claim all-memory recovery.
Expected under1sec;120sec guard; no timing/UI/TT/natural frequency claim.
