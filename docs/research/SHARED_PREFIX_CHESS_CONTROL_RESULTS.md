# Cross-game grammar and cost control

The original attempt is preserved as complete=false with no counts; the
observed cause was promotion_mode=none on nonpromotable native Chess patterns.
Legacy drop patterns were already omitted under the declared board task.
The earlier progress-message castling conjecture was corrected after inspecting
actual patterns; it was not an observed cause. No Core/rules or frozen Shogi
kernel was changed.

A separately frozen correction admits none only for native nonpromotable
origins, while keeping all path/effect/guard checks. All four independent
first/second counts agree: N20832/66472, B33936/85824, R53760/194432,
Q87696/162048. All249984 worlds remain per mode, including unreachable tails.

Eight grouped board patterns share16 geometric primitives:1792 candidates,
versus6496 per-pattern endpoints;1024 cached source tables. Complete compile
and count took0.094sec, preprocessing0.047sec, max quiet variants27. These are
actual recorded local timings, not a complexity or deployment guarantee.
No engine event, public transition or goal query was used. Three controls
check preserved failure/correction pins, whole counts and fail-closed promotion.

This establishes a cheap cross-game ordinary-board prefix seam despite grammar
encoding differences. It does not admit Pawn's auxiliary/forced promotion,
castling, held modes or full game legality. Next use shared-prefix tail bounds
and physical simulation constraints to retain decision information rather
than guessing a midpoint or fitting values to human order.
