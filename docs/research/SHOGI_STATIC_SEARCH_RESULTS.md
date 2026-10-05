# Production static search matches the saved finite tree

Frozen direct run_root_search with qdepth0, depth2, no TT/ordering/tactical
fallback/PVS/native provider reproduces both complete saved-tree references:
geometric_half selects promoted capture, score130057; unit selects native
capture within its two-action full tie, score200000. Both complete depth2 with
qnodes0 and no fallback. Every94 runtime push has a matching saved board,
hands, base/current/promoted profile, actor, ply and terminal;94 pops balance.
This is runtime integration evidence, not independent outcomes or public Player
configuration adoption. Root history was imported as stored; no deeper
continuous-check/repetition/TT equivalence claim is made.

The exact geometric coefficient LCM82590826496 is unsafe as a static-score
scale. Fixed100000 half-up quantization changes each coefficient by at most
1/200000. With at most two ordinary resources, leaf and minimax value error
is at most1/100000; pairwise error is at most1/50000. Min/max cannot amplify a
uniform leaf error. Complete reference ties after quantization agree with the
old exact ties; no rounding-selected law or scale. Unit is exact. HeldP/R=1
is an explicitly declared integration point, not a new hand-price model; the
earlier exact common-parameter proof remains stronger on that separate issue.

Costs:94 mutable runtime pushes, not public transitions;220 semantic candidates
and910 conservatively returned actions (including caches),0 source queries,
0 public events,0.125sec. Complete prospective128/5000/15sec caps respected.
Search stats:51/47 nodes,49/45 pushes,44/40 leaf evaluations; saved-tree
reference calculation is separate pure arithmetic, not another game search.
Method instrumentation restored in finally and frozen source hashes match.

No claim of material strength: prior finite mate-window result still says all5
choices zero. No old fixture deepening or goal budget reset. Next useful
question is search ordering cost under the SAME leaf evaluator, or extending
the qualified physical profile grammar. Freeze each distinct contract first.
