# Task041: identical RuntimeError text has distinct provenance

Six real S3 pairs pass under the one global/compat Task040 fixture. An unresolved token is returned as None. Exact checkpoint RuntimeError objects, deliberately using the same text, propagate at checkpoint1 and the final direct-transition checkpoint. Callback sequences, actual generated entry hits and full parents match original/shared arms.

Two direct baseline controls locate the declared final checkpoint. No Task040 comparison loop is replayed. Source setup initially omitted its internal clock, then stopped before installing the entry-hit wrapper; both failed sources/logs remain. Fixes restore the intended fixture and observer rather than weakening assertions or changing the six conditions.

Finite deferred-aux exception provenance is supported. No search, C, wall-time, allocation-failure, all-prefix, full-domain or deployment conclusion follows.
