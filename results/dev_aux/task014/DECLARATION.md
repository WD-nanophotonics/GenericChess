# Task014: opaque bridge allocation before migration completes

New question: can one real constructor failure after old imported occurrence
removal violate the published Runtime rollback contract?
Original b4108a68 and published558b497 push AST arms; remaining Runtime module
is AST-identical. No product writes, defaults, primary tests or Native calls.

Twelve cells (2arms x6contexts): complete3ply-cycle same-action control;
opaque3ply-cycle; opaque3ply forced RuntimeHash(0,0);
nested2ply opaque root with one ordinary outer push, then opaque bridge;
the same nested case with forced hash; ordinary initial root fresh-child ctor.
Bridge fault throws MemoryError exactly once from the _Occurrence constructor
when the active child frame has bridge_key and child_occurrence_added false,
at creation of a RuntimePositionIdentity target. Complete control cannot reach
this constructor because its target already has count1; retain unreached outcome.
Ordinary context throws once at new child constructor with no bridge key.

Retain actual count multiset, empty bucket/hash-key structure separately, aliases,
opaque imported keys, frames/history/context/root identity/hash/snapshot/cache,
and original/escaping exception with __context__. Other allocations succeed.
Expect bridge target creation to be reached and the old implementation to replace
MemoryError with AssertionError and lose imported count; if not, report no witness.
The ordinary-add case can retain an empty bucket but no count; do not label that
as lost repetition or TT corruption. Successful no-fault complete control
matches public apply_action and restores after pop.
No attempt to reuse corrupted bridge objects; discard them after evidence.
For nested failure inspect preserved outer frame without forcing a misleading
cleanup/pop of the already corrupt object.

Expected under2sec;120sec between-cell fuse; stop per cell. No timing or natural
OOM/UI frequency, no global exhausted-memory recovery claim. No new existing-target
bridge is manufactured: that branch does not construct a fresh target, so this
specific constructor premise cannot test it. Existing-count rollback evidence
Task008 remains under its original later-fault premise.
