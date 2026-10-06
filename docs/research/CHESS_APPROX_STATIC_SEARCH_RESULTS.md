# Five-mode material component works in actual Chess search

Five complete depth1/q0 actual searches equal their complete integer child
tables, with no TT/order/PVS/tactical/fallback. Exposed six-choice root:
geometric43761 and linear43717 uniquely capture N; unit0 captures B within
both-capture tie. Native initial position with full default castle rights:
geometric/unit both score0 and tie ALL20 legal actions. This opening test is
an implementation control, not discriminative usefulness or a strength gain.

All58 runtime pushes match stored full child position/ply/local-terminal
records,58 pops balance. Twenty NEW public initial children were separately
checked against20 pinned author pushes and the complete20-action parent set.
Effective castle slots all remain1 even though initial storage is empty;
all eight Pawn doubles carry exact corresponding author EP targets, the
others none. Fresh history length2/ply1, board/actor/automatic outcome match.
No source tables or new gameplay labels; small root remains exposed.

Metered new main0.188sec,20 public+58 runtime events and1444 returned/list/
membership entries. Including disclosed prior metadata diagnostic gives79
materializations and1484 entries; two compilations. Prefix elapsed and
semantic-candidate cost were not instrumented and are explicitly UNKNOWN;
do not claim a metered total/candidate bound for that prefix. It was a single
e2-e4 auxiliary probe, not secretly rerun. The bounded main15sec/128/5000
gates passed, not a statement that every acquisition cost was measured.

The evaluator is an explicitly approximate inventory feature that ignores
positional/auxiliary contributions while search retains complete legal
context. It does not declare current-position contact equivalence, normalize
away rights/EP/history or relax strict old adapters. Quantization uses fixed
100000 scale, error<=15 raw integer units for30 resources, pairwise<=30;
mate/static separation retained. Production evaluator/rules remain unchanged.

No source insufficient-material runtime adapter is installed: the two draw
states of the new exchange remain a different adjudicated task. Depth1
search here only touches source-qualified ongoing children. Extending its
depth must not silently claim normal Western automatic-draw semantics.
Next useful deployment step is a separately frozen decision-changing batch,
with exact context/goal/label information stated before any new sampling.
