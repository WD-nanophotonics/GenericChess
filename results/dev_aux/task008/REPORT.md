# Existing-count and bridge lifecycle candidate validation

All16 declared cells ran: original/candidate, complete/opaque/nested/forced-hash
collision contexts, before-history snapshot and after-history terminal faults.
Actual private entries copy numeric counts; equality includes root position,
identity/hash, persistent counts, played history/context, opaque keys, aliases,
frame depth, cached frontier and bindings.

Eight candidate cells restore exactly after the exception and after successful
same-action push/pop; all ordinary child positions/terminals equal public
apply_action. Original complete-witness snapshot cell fails both restoration
checks even though table entry count remains4: an existing child's count is
incremented, rather than a new entry created. Thus checking only table size
also misses a defect. Other seven original cells restore.

Opaque cells actually record bridge=true; complete cell records bridge=false.
Terminal injection is after append, and snapshot injection is before append.
Nested contexts retain then pop an outer frame. Forced RuntimeHash(0,0) retains
collision-aware exact entries. Candidate does not double-remove in these cases,
and does not remove the prior existing child count. Immutable table equality
is the evidence, not the compatibility projection or cumulative stats.

This is a small deterministic cycle fixture, not all generated rules, all
allocation points or the installed full Native search. The private candidate
was never written into tracked product source. No throughput measurement or
search budget claim. Dot's n>0 concern is covered by existing-count cells;
broadening into more games without a new failure premise is deferred.

Reproduce: .venv/Scripts/python.exe results/dev_aux/task008/lifecycle.py
Result lifecycle.json,16 cells. Source remains the pinned b4108a68 baseline.
