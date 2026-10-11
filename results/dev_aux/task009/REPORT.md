# Occurrence-table oracle calibration

Four predeclared corruption sentinels ran and were undone exactly.
Multiplicity-preserving immutable Counter entries detected all four: count
increment, fresh child entry, exact duplicate entry and moving a hash bucket.
The set-based oracle missed the identical duplicate. Root compatibility
projection changed in none. Table size also missed increment and bucket move.

These are deliberately invalid private states to calibrate detection; there is
no evidence here that normal code naturally creates duplicate identical entries.
Task006/007/008 raw data and conditions are untouched. They detect the concrete
count leak, and their set-based comparison scope is now explicit. Future
restoration audits should copy numeric counts and retain multiplicity using
frozenset(Counter((hash, identity, int(count))...).items()).

The one-conjunct candidate only removes/decrements a child, and existing
_find_occurrence/bridge restoration search exact existing entries before adding.
The inspected ordinary flow retains one entry per exact identity in a bucket.
This explains why the duplicate sentinel does not itself demonstrate another
candidate failure; no arbitrary new rerun or larger game test follows.

Result calibration.json, four bounded cells; no engine search or timing.
