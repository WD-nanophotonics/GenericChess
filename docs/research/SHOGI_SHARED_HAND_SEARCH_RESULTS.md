# Shared held coefficients: choice stable, score changes

The frozen protocol reuses all43 saved physical leaf states, with board weights
P7711, TP30057 and R96770 at scale100000. One vector hP,hR in[0,1] is shared
across the entire tree. Exact affine minimization certifies each reply minimum
over the FULL box, rather than independently optimizing each leaf parameter.

The three quiet branches have minimum -9677/10000-hP. Native capture has
7711/100000+hR; promoted capture has30057/100000+hR. Thus promoted minus native
is exactly11173/50000, and promoted minus each quiet lies in
[126827/100000,326827/100000]. The unique promoted capture is certified for the
whole continuous box. This is saved-tree arithmetic, not a claim that the
production program was executed at every hand vector.

One new actual depth2/qdepth0 search at hP=hR=0 returns score30057 and that
unique choice. The old h=1 search is reused, not rerun: score130057 and the
same choice. The100000 score difference is precisely the captured base-R hand
term; zero hand is neither a zero evaluator nor an admitted hand coefficient.
Actual legal hands, base/current identities and transitions remain unchanged.

All49 new pushes match the saved physical positions and are balanced by49
pops. The run completes depth2 with51 nodes,44 evaluator calls, no qnodes,
ordering, TT, native legality or root fallback. Paired cost is98 pushes,
conservatively1707 enumerations and0.234sec, inside the unchanged128/5000/15sec
caps. There are0 public transitions and0 independent source queries.

Evidence: data/shogi_shared_hand_search_20261006.json and the protocol/producer
pins therein. This extends integration beyond the previously declared h=1
point. It does not identify a useful hand price, prove all-box production
equivalence, improve the old ply3 mate window, establish eventual WDL or admit
the scientific material prior.
