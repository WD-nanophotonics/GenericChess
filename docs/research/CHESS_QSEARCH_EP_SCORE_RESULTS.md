# The omitted capture changes an actual qsearch score

Different fixed synthetic game root K(a1)/P(e5) versus K(h8)/P(d7),Black
to move. This explicitly starts a new game at that root, not fictional
native-initial history. Public d7d5 creates the real EP token; all five White
children match full-stack pinned source board/history and are ongoing,
nonchecking. Source/local complete actions match. Captures are only e5xd6.

Actual existing quiescence call returns0 and misses that action. Temporarily
installed research complete-child classifier returns17417, exactly the fixed
geometric prior's quantized Pawn and the independent all-noisy-child reference.
qdepth1,harddepth2,full window,no TT/order/first-iteration reserve. Original
one qnode,adapter two qnodes; no abort/fallback. Neither call changes root
position,ply,terminal,history,counts/hash;11 total probes/pushes equal11 pops.
Stats' runtime fields remain zero because this direct internal audit never
attached stats; the separately instrumented top-level counts are authoritative.

6 public transitions/6 source pushes,88 local returned/membership entries,
10 source entries,one compilation,0.047sec. Old call costs5 classification
pushes/30 entries; adapter6 pushes/38 entries. Therefore completeness does
have a measured price. This is semantic integration, not WDL or performance;
the synthetic material score is not an independently solved game value.
Production source is unchanged; monkeypatches are restored in finally.

A subsequent cheap capture-effect hint preflight fails before any31 saved
action comparisons; its generic error did not identify the first offending pattern.
CHESS_CAPTURE_EFFECT_HINT_PROTOCOL.md and frozen raw record retain that
failure/one compile/0 transitions. Executor source explains clear_right is
aux-only, while set_current_type preserves owner/board occupancy. A versioned
constructor must deliberately admit these real effects, not rewrite the old
helper/output or assert unqualified metadata integration. Actual expensive
adapter remains useful as an independent correctness oracle.
The separate structural pass identifies FIRST unsupported effects as
remove_from_hand/place in inactive drop catalog entries, not clear_right.
V1 also rejects clear_right later; V2 admits it but still fails on drop entries.
See CHESS_CAPTURE_EFFECT_V3_RESULTS.md for the explicitly changed board scope.
