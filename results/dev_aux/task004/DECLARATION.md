# Task004: thin-backend max-ply precedence with complete played history

Independent DEV_AUX finite counterexample search, pinned b4108a68 product.
Question: do Core and the specialized thin adapter agree on terminal precedence
at the declared1000-ply boundary, with real replay history and exact restoration?
This is a new semantic boundary, not a timing rerun or evidence of generality.

Two fully legal synthetic Chess paths share996knight-cycle plies
(g1f3 g8f6 f3g1 f6g8 repeated249times). A adds g1f3 g8f6 f3g1,
then black e7e5 should yield max-ply draw. B adds f2f3 e7e5 g2g4,
then black d8h4 should yield mate rather than max-ply draw. Repetition threshold
is100000, so these histories cannot trigger it. No human game data involved.
Replay via public Core actions and independent python-chess move validation;
retain every Position witness. Do not set ply_count/history by hand.

At each999ply parent, compare full legal labels, material, terminal and all
one-ply children (finite frontier). Compare material-only minimalAB D1 results
and non-time work/trace for Core versus specialized adapters under4096nodes,
10seconds/call. Check selected draw/mate child terminal status independently.
After each child/pop require full Position, ply/status, identity/hash, counts,
snapshot, history/context and frame restoration, not merely board equality.
Inject one failure at terminal adjudication after child history update, then
require the same restoration before an ordinary legal push succeeds.
No Native kernel correctness claim or speed comparison. Core owns semantics.
120second batch fuse, no extra workers/compilation, interruptible between moves.
Wait until primary's granted timing slot ends before this short count-only run.
An illegal/unreached parent or cap remains a reported failure, no substitute.
Expected cost under two minutes; compare only two declared synthetic histories.
