# New partial-stock promotion/custody use contract

This is a synthetic mechanism test outside the strict full-stock Shogi adapter;
do not weaken that adapter. Fixed fresh board: owner0 K45/P54, owner1 K65/R63,
empty hands/aux, side0, normal Standard Shogi rules/history. This root is chosen
before actions/scores/goal observations to expose optional promotion on a Rook
capture. It is not a natural-frequency sample or historically reachable stock.
Reject if terminal, previous mover checked, or board equals an old observed root.

Expand the COMPLETE root and COMPLETE opponent reply tables, terminal first,
static depth2 minimax, canonical lossless-ID tie. Both previously frozen board
contact laws use their complete exact board means/common TR scale; never mix
laws. Unit/zero baselines share the same full tree. Board features use current
type, hands use captured base. Treat hand R and P as UNKNOWN common parameters
in[0,1], with one parameter vector shared by ALL leaves. This box is a declared
uncertainty scope, not a guess of hand price or constructor output. Declare the
partial-stock static approximation explicitly even on checked ongoing leaves.
No official-goal/royal-survival lower-bound interpretation of static scores.

Certify complete tie sets only if each branch's leaf inventory is constant, or
some leaf is coefficientwise no better than every other leaf over the shared
box. Its affine score then equals the true branch minimum throughout the box.
Compare those affine minima by exact margin extrema; do not sample parameters.
Retain unsupported/noncertified branches whole rather than falling back.

Freeze all selections and full ties BEFORE independent goal work. Independent
target: owner0 checkmate within two own actions (ply3) against ALL opponent
replies. This finite target is not eventual WDL; ongoing frontiers remain
unknown for eventual goal. Admission first computes prospective full next-ply
width on the same saved depth2 states. Once a lower bound plus existing public
events exceeds128, stop width examination and retain an explicit over-budget
unknown goal; do not enlarge budget, pick favorable replies or run partial
mate experiments. All methods/full tie unions receive that uncertainty.

Whole study caps128 public transitions,128 actions/node,5000 enumeration
(including apply membership work and goal-width preflight),15sec. One fixed
root only, no symmetry batch or prior old fixture expansion. Inputs and
prelabel selection snapshot pinned; no source/human/holdout labels or rerun.
