# Reachable history limits of Native trace targets — 2026-10-19

This separate supplement follows the 2026-10-18 trace study. It does not change
the earlier sealed results, run a learner, or modify another Agent's checkout.

The existing coordinate-free Pass fixture was explicitly refused by Native.
Here ordinary supported reversible moves provide the independent alternative:
a forced four-cycle, then two independently reversible pieces per player.
Every parent is reached through public GameSession.submit; all state, history,
records and witnesses are retained. No history was fabricated or shortened.

24 cold Native queries use 1600 nodes in 0.21155 producer seconds, within the 32-query count cap. Eight unused slots are closed. The intended
continuous 120-second clock was not enforced across the staged Agent work;
see budget-deviation.json. Producer-time sums are not the elapsed stage span.
These are mechanism fixtures, not random rule samples or strength evidence.
The material-only profile uses the supported integer scale 1, not Native256.

The Core reader builds 1048 visits / 1028 edges and replays 50 PV edges for
the first 20 queries / 310 retained trace rows. Every root is correct. Every
emitted trace bound has at least one valid matching complete Core context.
A branching query nevertheless has an interior EXACT -2 row at remaining
depth 1 / search ply 7 whose position key also describes a valid value-0
history. The missing path prevents identifying its actual source context.

Four additional D1 queries replay those two complete histories separately:
same board, same side, same rule, same ply 7, different history/counts.
Both modes return the correct distinct EXACT root targets -2 and 0 under
the same trace key. The canonical record reader independently checks all
four children and both records. Root correctness is not an engine bug.

Keep complete query provenance, but it alone does not recover an interior
path after within-query deduplication. Position-key pooling cannot promise
exact history-conditioned target reuse. A deliberately averaged approximate
target would be a distinct learning method requiring stated assumptions.
Current published AUX93 still uses Core float/path credit; no Native trace
migration, new diagnostics API, source path export or dedup policy is adopted.

Run qualify.py from the repository root to regenerate two outputs from the
two established hash-pinned source archives, Python -S, without Native.
Both outputs match apart from elapsed seconds (private 1.987 seconds;
public-copy verification 1.928 seconds observed).
This verifies finite recorded contexts, not every generated rule or WDL.
Two new product regression controls cover the actual same-ply histories and
both root-window modes. Only a comment is added to the result-field contract.

Setup failures are retained: a wrong PieceType attribute, a failed shell
repair followed by a second zero-query launch, and an initial reader attempt
to treat lossless dataclass receipts as the canonical wire record. The fixed
reader legally replays every recorded action and validates the full record.
These are producer/reader errors, not automatic approval or Native failures.
