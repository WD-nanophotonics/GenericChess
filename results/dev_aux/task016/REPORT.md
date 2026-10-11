# Old-entry equality failure after successful target preparation

Four declared controls complete. Public repetition mapping is unchanged by
tuple-order permutation, imported through normal opaque from_state. Forced
hash0 puts distinct exact identities in one bucket; target old key is last,
so list.remove executes earlier-entry comparisons. Original dataclass
_Occurrence.__eq__ disassembly contains two BUILD_TUPLE instructions. Injection
selects only that real comparison in _resolve_opaque_history_key and hits once.

Both no-fault original/target-first controls agree with public Core and restore.
On published558b497 comparator failure, old entry was not removed and table
restores, but rollback still raises missing-target AssertionError with the
MemoryError object in __context__. On the frozen target-first working candidate,
the exact MemoryError escapes, but old count1 becomes2: target was installed
and journaled, old removal did not happen, then rollback adds old_count to the
still-existing old entry. All recorded root fields restore while actual counts,
snapshot.items and snapshot.digest consistency fail.

This distinct operation narrows full exception-safety claims; it does not
withdraw Task015 constructor-fault acceptance. There is no natural OOM rate,
global memory immunity, real UI impact, TT cutoff or timing claim. Damaged
objects are discarded. The mapping permutation changes representation order,
not count/legality semantics; no inconsistent private table is inserted.

A decision-changing fix must know whether destructive removal actually occurred,
or avoid fallible equality after committing target storage (e.g. identify the
old slot before mutation and delete that exact slot). Merely rethrowing the
original exception is insufficient. Primary owns repair/publication; this
branch contains only independent frozen evidence.
