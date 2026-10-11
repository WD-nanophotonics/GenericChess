# Task004 full-history terminal boundary validation

Pinned b4108a68 source; two synthetic complete played histories, no human data.
Both999-ply parents are reached by996legal knight-cycle plies and three
declared moves. Every Core transition uses public legal actions; python-chess
validates the same moves independently. History has1000records and1000Position
witnesses at each parent; no hand-set ply counter or history truncation.

All52legal one-ply children (22draw-parent,30mate-parent) match between Core and
the specialized thin adapter in complete board/aux state, material and terminal
score. At ply1000, e7e5 gives MAX_PLY draw; d8h4 in the other path gives checkmate
with winner1 and root score999999999. Mate takes precedence over the ply draw.
Identical minimalAB D1 work and trace select a7a5/0 on the all-draw parent and
d8h4/999999999 on the mate parent. Backend agreement does not imply optimal play
beyond these finite material-only D1 controls.

Every child/pop restores Position, ply/status, identity/hash, repetition counts,
snapshot, history/context and frames. Injected terminal failure after history
update also restores all these fields at both long-history parents, and the
same action succeeds afterward. This extends the earlier short-history
rollback scope and checks the thin adapter's declared1000-ply policy on full
played history rather than a fresh-FEN clock approximation.

Boundary.json and boundary_audit.py preserve the fixed inputs, source hash,
per-child outcomes and non-time trace/work. No Native kernel, timing, FIDE
claim-draw, all-rule correctness or hard-latency claim. The repetition threshold
100000 cannot be reached by these1001-record paths. The batch was run after
the primary's first five-minute reserved timing slot ended; its engine process
has exited. Source product remains unchanged.
