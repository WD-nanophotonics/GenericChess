# Independent target-entry obstruction lemma

Freeze2026-10-06. NEW question: are the352 known corner-target worlds all
obstructions caused purely by no possible final capture edge? This is not
the full Horse reachability complement, SCC census or old target slab query.
No compiled geometry, per-world BFS, source/capture/game event or full graph.

For targetT=(x,y), diagonal signs(a,b) in{-1,1} produce common incoming leg
L=T+(a,b) and potential sources S1=T+(2a,b), S2=T+(a,2b) when inside9x10.
Each source's final capture is forbidden by blockerB iff B=S or B=L;
B is distinct fromT. Thus all incoming edges vanish exactly when B belongs
to the intersection of {S,L} across ALL in-board incoming sources. Empty
intersection means at least one unblocked final edge, not reachability from
an arbitrary starting square. The existing passive target cannot equal its
own incoming leg; stationary blocker semantics preserved.

Enumerate90 target coordinate classes,8 nominal offsets each720 checks,
plus ONE set-intersection operation per actual incoming edge. Historical
analytic prefix has508 actual edges; charge<=508 intersections. Total<=1228
new analytic terms, existing3732 =><=4960 under the original5000 cumulative
term cap.0 new forward nodes, existing1579 untouched.15sec cooperative
clock. No more cases on failure, no full native graph or enlarged budget.

Expected falsifiable statement: only four board corners have a nonempty
intersection, the single inward-diagonal leg. Each such T/B pair eliminates
all88 allowed sources, totaling352 previously known worlds. If wrong, keep
the counterexample and do not assume400 known zeros complete. If true, it
qualifies only the no-final-entry subset and leaves connectivity/escape gap.
