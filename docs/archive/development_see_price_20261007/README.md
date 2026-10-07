# Isolated fast SEE arithmetic-price contrast

This experiment changes8arithmetic reads inside pinned Position::see_ge to
CapturePieceValue, including the5ordinary recapture constants. Attackers retain
the old Pawn/Knight/Bishop/Rook/Queen order; capture ordering and all search
thresholds remain unchanged. It is partial price consistency, not generic SEE.

Both private binaries share an identical diagnostic gcsee command, the unchanged
half-risk evaluate object and26other native objects. Original sources/binaries
and production/default configuration are unchanged. A single ordinary QxP/PxQ
fixture and its color mirror produce36predicate calls; corrected price agrees
with all expected thresholds. Original unit pricing disagrees on2cases. Six
complete static eval trace pairs are identical. These fixtures do not certify
arbitrary exchanges, pins, special captures or general search correctness.

Eight exposed common roots change2choices. The retained linearBlack failure
changes c6c5 to g6f5 at1/4sec, with finite referencecp-866/-861 respectively;
both remain poor. Full Core history/legality and20choice/6reference PV checks
pass across9roots. Finite cp/mate is not independent exact WDL or a safety proof.

The fixed12direct price/original games finish2W2L8U:geometric2W2U,linear4U and
unit2L2U.1825played+48prefix plies replay with zero mismatches. No established
overall improvement; neither unfinished nor finite child cp is a strength score.
[Portable results](../../research/data/chess_see_price_20261007.json) bind raw.zip,
sources.zip and entry hashes in index.json. All30entries were physically extracted
and rehashed. Measured wall1822.984s; recorded price/original search897.748/901.633s,
record saving10.976s; other12.627s unseparated. Node reports are not equal-node
conditions; each side has the same1second search condition.
This is exposed development, without price/weight fitting, holdout admission,
default promotion. User2026-10-07 authorized publishing Agent-generated evidence;
actual remote SHA is checked separately after commit/push. Archives are historical records,
not active workflow policy. Restore into an isolated directory and compare every
entry to index.json; upstream source pin/GPL notice are retained with sources.

## Declared follow-up, not executed

[Next fixed2400 plan](../../research/data/chess_see_feedback_next_20261007.json)
binds the separately named next-feedback-games.py and next-feedback-replay.py
exports by hash. These are prospective source copies, not results in raw.zip.
Restore them as games.py/replay.py in .local_agent/see-feedback-20261007 with the
plan copied to declaration.json in a matching checkout; restore the qualified
private binaries/config first. Do not run these archive copies in place.
