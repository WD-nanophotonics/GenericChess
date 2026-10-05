# Independent Shogi mate-source contract

The author-owned source was resolved directly to commit
c1b80eaa09fe13d5f12b1599d1ae4d53c224de30. Four complete source files were saved
and hashed,77532 bytes. The overall acquisition remained FAILED: its final
license request encountered the120KB sentinel limit (120001 cumulative bytes),
so the license body was not written. Preserve this partial evidence; no
executable, full source package, license-complete distribution or source label
was acquired. Cached web master views were not used as immutable version proof.

The move picker generates checks for attackers, evasions for defenders, and
filters illegality. Its complete-generation variant includes underpromotion.
This suggests a restricted checking strategy may prove a full-game win if
every local defender action is covered and every action is locally legal;
it does not make restricted no-mate an unrestricted goal result.
[Author source](https://github.com/yaneurao/YaneuraOu/blob/c1b80eaa09fe13d5f12b1599d1ae4d53c224de30/source/mate/mate_move_picker.h).

The odd-ply solver has additional asymmetric limits: its three-ply path rejects
a defender counter-check rather than solving it, and its one-ply shortcut
returns no result if the attacker is checked. Thus failure can arise from
search scope even with no resource timeout. Positive results still require
local terminal/history replay; negative transfer is especially unsafe.
[Author source](https://github.com/yaneurao/YaneuraOu/blob/c1b80eaa09fe13d5f12b1599d1ae4d53c224de30/source/mate/mate_solver.cpp).

DFPN's exposed PV follows one child at each alternating node; it is not an
exported all-defense proof tree and is not guaranteed shortest. A printed line
ending in mate cannot by itself prove every defender reply loses or establish
exact DTM. A future adapter needs a qualified complete-tree export or bounded
local all-defense reconstruction; a source hash cannot substitute for that.
[Author source](https://github.com/yaneurao/YaneuraOu/blob/c1b80eaa09fe13d5f12b1599d1ae4d53c224de30/source/mate/mate_dfpn.hpp).

The mate engine distinguishes timeout, unresolved/no-result, restricted
nonmate, and a mate PV. Its mate command parameter is time rather than proof
depth. None of these operational details supplies a general WDL label.
[Author source](https://github.com/yaneurao/YaneuraOu/blob/c1b80eaa09fe13d5f12b1599d1ae4d53c224de30/source/engine/yaneuraou-mate-engine/yaneuraou-mate-search.cpp).

Decision: do not run/build/install this engine or obtain outcome-selected
problem roots now. The useful NEW next action is to establish whether a small
complete AND/OR proof export already exists at this pinned source, or whether
a published independent tree certificate can be replayed within128 events.
Freeze root-selection and prior/search/tie intervention before exposing labels.
If only a PV exists and local closure is over budget, retain unknown; external
solver computation must not be hidden as cheap local validation. Match full
board/hand/origin/rules and histories, all legal counter-check/underpromotion
and pawn-drop-mate rules; official Shogi stalemate scope remains separate.
Positive replay certifies a strategy/horizon upper bound, not shortest DTM.
This source opportunity is separate from increasing the old failed window.
