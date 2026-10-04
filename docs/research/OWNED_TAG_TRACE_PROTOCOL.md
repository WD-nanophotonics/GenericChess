# Owned-tag ordered-effect semantic controls

Frozen before adapter-control execution, 2026-10-04. No material coefficients,
goal probes or new random contexts. Both actor directions, five fixture kinds:
Chess castling (track secondary Rook), Chess en passant (track off-target enemy
victim), Shogi Pawn promotion (track same owner's base P/current TP), Shogi Gold
drop with two own held G (track one exchangeable hidden tag), Shogi R capture
of enemy promoted P (tag loses ownership although its base joins the other hand).

Chess FENs: 4k3/8/8/8/8/8/8/4K2R w K - 0 1 and
4k2r/8/8/8/8/8/8/4K3 b k - 0 1; castle e1-g1/e8-g8.
EP: 4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1 and
4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1; e5-d6/e4-d3.
Shogi anchors K0 at(0,0), K1 at(8,8). Promotion P at(4,6)/(4,2), move to
(4,7)/(4,1) with TP branch. G drop to(4,4), actor hand count2, no ordinary board
pieces. Capture R(4,4) to enemy TP(4,5)/(4,3), no initial hands.

Use exact verified semantic binding/ordered resolved operands and authoritative
public apply_action. Research adapter may inspect pinned reference private
resolvers, but must not modify production execution. Trace projection must agree
with full authoritative board/hands; compare full histories separately. Initial
tag probability1, no persistent UUID invented. Uniform hidden hand selection
gives held1/2 and dropped1/2; enemy capture yields lost1 and own-survival0.

Support move/shift/remove/type and a proved count1 remove_from_hand/place pair.
Unsupported creation/unpaired/multi-count hand effects fail closed. Aux effects
retain authoritative future state but do not relocate the tag. Exact mass
conservation and initial/final owner/base/location support are required.

Caps:10 seconds for both game compilation and all controls,128 enumerated legal
choices/root,512 total enumerated choices,10 actual public transitions. Failure
is incomplete, no larger-budget retry or replacement fixture. Control tests may
verify synthetic algebra/invalid traces independently; no rerun of old service
or outcome experiments. Report every fixture/action, exact tag mass, mode,
boards/hands/history, elapsed time and frozen program/source hashes.
