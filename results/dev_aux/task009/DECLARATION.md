# Task009 independent occurrence-oracle multiplicity check

New decision: immutable set or table-size equality can mask an exact duplicate
private occurrence entry, and count equality must retain bucket multiplicity.
This is oracle calibration on synthetic corrupt state, not a natural product
failure claim. Preserve Task006/007/008 outputs unchanged.

One ordinary complete-history initial Chess Runtime. Four bounded sentinels:
increment an existing count; add a fresh unrelated exact child entry; duplicate
an existing identical identity/count in its same hash bucket; move that existing
entry to a different hash bucket. Restore exact table after each sentinel.
Compare existing set-based oracle with an immutable multiset Counter of
(hash, identity, numeric count). Every multiset oracle must detect a sentinel.
Expected only identical-duplicate cell evades set oracle. Root compatibility
projection is also reported but never used as authority. No push/engine search,
timing, product changes or additional worker. Then choose a shared multiset
helper for future audits; do not rewrite old results as newly independent.
