# Soldier forced-prefix and monotone-rectangle certificate

Prospective question: independently qualify the entire saved Soldier distance
histogram without repeating the9x10 compiled census. Width W>=2,height H>=2,
river entry row r in1..H-1; owner0 forward increases rank. Adjacent forward
moves everywhere, adjacent lateral moves only from rank>=r, never backwards.
One stationary own blocker, passive enemy target; no royal/history legality.

For distinct source/target ranks s,t and file difference k, base distance is
t-s+k when reachable. Below-source targets and below-river lateral targets
are unreachable. Below-river source has a forced vertical prefix through r
when target is above r, or to target when same-file target<=r. A blocker on
that prefix makes contact impossible. Same-rank lateral contact has a unique
path and an interior blocker makes it impossible, including target rank r
after crossing. Above-river same-file vertical interior blockers require two
extra lateral steps. Above-river rectangles with positive height and width
have two shortest elbow routes with disjoint interiors: one blocker leaves
a shortest route. All other blockers leave the base distance unchanged.

Count ordered file pairs by k: W for0,2*(W-k) otherwise. Aggregate over rank
pairs and k, never over blockers. Freeze cases and formulas before checking
the saved9x10 histogram. No context-law choice, fitting or new human labels.

Fresh independent coordinate BFS: all504 distinct triples on3x3 river1;
on3x4 river1 exactly18 source-target pairs: (0,1),(0,2),(0,3),(0,4),
(0,5),(0,6),(0,7),(0,8),(0,9),(0,10),(0,11),(3,5),(3,9),(3,11),
(6,8),(6,9),(9,11),(11,0), all10 blockers per pair. Total684 worlds,
at most5000 expanded nodes/15sec. No theorem shortcut in BFS. Preserve
partial/failure record, no cap increase, reset or enlarged follow-up census.
Compiled/canonical geometry, runtime/public transitions and source calls0.
Owner reflection is an analytic coordinate symmetry, not compiled per-world
owner1 admission. Match full histogram aggregates, not every full-board label.
