# Debug-tree export qualification gap

Follow-up inspection of the same pinned mate_dfpn.hpp finds dump_tree near
line655. Unlike exposed get_pv, it attempts recursion over children with pn0.
It prints a path even when children are absent or child_num0, and prints
'mate not found' if no solved child is found. Missing child storage is not a
local terminal-mate certificate. Thus this opportunity must not be dismissed
as PV-only, but the debug text is not yet a qualified all-defender proof export.

Before any execution determine template/build reachability, child storage
layout and reclamation, whether every AND legal reply is enumerated, and how
no-children lines distinguish proven terminal mate from unavailable storage.
Export must preserve full board/hands/history, node parity and rule admission;
local replay must verify defender closure and terminal obligations. Traversing
only pn0 children cannot establish closure without the full legal reply set.

No solver/build, labels, public events or byte-budget expansion. This is a new
metadata action on already acquired source, not a replacement of failed
acquisition status. The next memo source task now has a concrete debug-export
entry point, rather than assuming no recursive export exists.
