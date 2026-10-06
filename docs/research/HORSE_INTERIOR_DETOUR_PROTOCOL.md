# Small directed bypass lemma, with both occupied leg holes

Freeze before24 edge checks. H still treats BOTH fixed own blocker B and
enemy target T as occupied legs until capture; never reuse target-free graph.
For an ordinary Knight edge blocked by a center O=(0,0), canonical endpoints
(-1,0)->(1,1), substitute
(-1,0)->(0,-2)->(2,-1)->(1,1).
Its legs are(-1,-1),(1,-2),(2,0),never O. Check all eight signed/axis-exchanged
orientations,three edges each; all vertices/legs stay inside Chebyshev radius2.
If B,T each have board margin>=2 and distance_inf(B,T)>=3, every substitution
around one occupied center avoids the other. This is a sufficient SUBSET,
not the full400-zero complement or full distance histogram.

Primary graph input: Allen J. Schwenk,Mathematics Magazine64(5),1991,325-332,
https://www.math.cmu.edu/~nkomarov/21-110/knighttour.pdf,pp326 theorem.
The paper characterizes closed ordinary Knight tours.9x10 is admitted; remove
B from one Hamiltonian cycle to obtain a connected spanning path. Follow
that ordinary path from S toward T and replace every edge blocked by B or T;
final capture's leg cannot be T and B is far. Each substituted path avoids
both holes; stop on first T arrival. This uses a published graph theorem,
not a locally generated Hamiltonian witness or compiled-H census.

Charge24 directed edge motifs plus10 displacement-count terms for the central
5x6 rectangle. Continue prior4960/5000 analytical budget,ending4994;zero new
forward nodes(1579 retained),game events,compiled/slab queries. No graph census.
Derive pair count arithmetically:30^2-[sum_{d=-2..2}(5-|d|)]*
[sum_{d=-2..2}(6-|d|)],then88 sources per ordered B/T pair. Never treat this
subset mass as additional to tau1/tau2 without an overlap certificate.
15sec; failed path/budget closes record without rerun or altered stencil.
