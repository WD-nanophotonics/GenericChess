# Recursive export is a source opportunity, not an operational certificate

Pinned author source c1b80eaa09fe13d5f12b1599d1ae4d53c224de30,
mate_dfpn.hpp SHA52ddc75fde42b1879f758f001203c6e3ce8919d74a269978838b378605b23b75.
No additional acquisition, build or solver execution. Source snapshot read
locally; observations below do not establish all repository build variants.

The available NodeManager defines get_children, not the get_nodeptr referenced
by dump_tree. DFPN32 stores children as an integer index, while the debug
function directly subscripts node->children and assigns a child's children to
a NodeType pointer. DFPN64 stores pointers, but still lacks this get_nodeptr
member in the inspected manager. The only external call visible in this file
is commented inside #if0. These are concrete reasons not to assume the debug
function is callable. No compiler result or whole-repository absence claimed;
dependent-template lookup may leave unused code uninstantiated.

Allocator uses a contiguous buffer and monotone node_index during one search,
then reset_counter at next root or release on reallocation. Export must occur
before these operations; use node_manager.get_children to abstract32/64 layout,
and reject unavailable/CHILDNUM_NOT_INIT/out-of-memory storage as UNKNOWN.
Do not patch external vendor code or allocate an engine merely to test metadata.

More fundamentally, a childless solved node is not necessarily terminal mate:
WithHash closes nonroot proven nodes with child_num0, without reproducing the
subtree. Hash decisions use board/root-color plus hand-superiority comparison;
root may retain one move only. mate_1ply creates a compressed mate child, and
mate_repetition can close nodes with route-dependent conclusions. Max-game-ply
can also return nonmate. Fixing the debug accessor does not remove these proof
gaps. Printed paths omit full position/history, legal reply list and leaf cause.

Positive local strategy validation can ignore source pn/dn as hints: at each
attacker node replay one locally legal action; at every defender node enumerate
ALL local legal replies; apply local terminal/declaration rules first. Missing
continuations or source compressed leaves remain unknown unless local terminal
replay certifies the desired goal. A strictly decreasing horizon bounds cycles
without arbitrary transposition merges; imported history remains required.
Source checking-only attacks may produce a valid positive strategy, but source
nonmate is not unrestricted local WDL. Local pawn-drop mate/countercheck and
underpromotion defenses cannot be omitted. This is already supported by the
public-goal interval primitives; no new transport/certificate framework needed.

Decision: debug-export repair alone is insufficient. Prefer a bounded local
all-defense reconstruction using an externally proposed strategy, with root
selection/protocol frozen before labels and explicit compressed-leaf uncertainty.
The current four-file source opportunity remains unadmitted. No need to wait
for it: actual search integration and physical-profile qualification continue.
