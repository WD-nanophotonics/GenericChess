# Coupled capture construction: assumptions before coefficients

Question, 2026-10-04: can weighting a capture by the victim's own structural
capacity produce information absent from untyped capture opportunity? This is
a construction investigation, not a fitted rescue of V2D, V2H or local service.
No human references, old global deployment labels or Xiangqi holdout are read.

## First premise and its direct defect

Let c_i be a source-averaged expected count of distinct ordinary-victim
removals by type i. Suppose the type of each removed ordinary victim,
conditional on the untyped event, has a common distribution p_j independent
of source type, square, blockers and event identity. Count each physical
victim once; promotion choices cannot multiply a removal. The type matrix is
K_ij=c_i p_j. The independence premise, not the compiled rules, implies this
factorization. An anchor must be excluded from the ordinary-victim category
before defining p; an untyped enemy category containing anchors is insufficient.

For any positive proposed values v, Kv=c(p^T v). A positive right eigenvector
with nonzero eigenvalue must therefore be proportional to c. Its eigenvalue
is p^T c. Recursive victim weighting adds no relative-type information under
this premise. Normalizing rows instead makes all rows equal to p and loses
even offensive capacity. Adding a separate mobility vector b gives
v=b+beta c(p^T v), which introduces a mixture and beta; recursion does not
independently determine those choices. The defective *independent victim-type*
construction is rejected. This does not reject typed geometry or legal-state
coupling, where conditional victim type can depend on the event.

Source inspection: intrinsic_action_events.py's keys retain actor type,
destination, physical removals and resulting actor type, but occupancy cubes
use only empty/own/enemy. Its supported exact guards also lack victim-type
labels. Current events thus cannot directly estimate a typed K. V2C's coarse
source occupancy model does not provide the missing typed disintegration.
ADR126 counts removals; ADR127 recursively values actor promotion alternatives;
ADR129 weights same-domain capability; ADR130 records projected reachability.
None of these is a victim-value fixed point. Their old numerical freezes are
not recomputed or repurposed here.

## A changed premise worth testing

Type-dependent placement support can break that factorization. Before a
coefficient batch, check a deliberately sparse two-token intrinsic law. Define
each type's active support from a compiled board event possible on an otherwise
empty board with either no enemy or one enemy. Sample owner uniformly and the
actor/victim square pair uniformly among distinct squares of their respective
supports. Record whether at least one intrinsic action removes that victim.
This is an explicitly new, pair-conditioned diagnostic law, not full-inventory
Q, strategic visitation, initial reachability or verified legal-game play.
Immobilized tokens are excluded by a modeling convention, not a legality theorem.

First compare all-square exchangeable support with active support. Compute
only exact capture incidence matrices, identical-column groups, rank and an
explicit nonzero 2x2 minor. Do not compute eigenvector material values yet.
Rank>1 would show new input information, not usefulness. Failure to obtain it
rejects this changed premise as a source of coupling in the tested scope.
Success still leaves the appropriate positive/negative feedback interpretation,
victim frequencies, promotion and hand value unresolved.

## Primary precedent and limits

[Bonacich 1987](https://www.cse.cuhk.edu.hk/~cslui/CMSC5734/Bonacich-Centrality.pdf),
pp1172-1174, gives eigenvector and parameterized recursive network measures.
Its discussion distinguishes reinforcing communication links from competing
exchange links and warns that network importance omits other relevant factors.
This supports the mathematical family, not chess utility or a parameter choice.
Our inference: an attack edge may represent denial of an opponent's capacity;
walking repeated graph edges is not executing repeated legal captures. Neither
positivity nor a Perron solution alone licenses a material-price interpretation.

[Barthelemy 2024](https://arxiv.org/html/2410.02333v1), sectionII, uses a
position's attack/defense graph and betweenness to measure fragility. That is
a state statistic, not this type-level static construction. We do not reuse
its graph walks as legal continuations or import game data as coefficients.

## Next decision

Run the separately specified cheap incidence diagnostic. If it exposes genuine
typed information, determine a defensible finite interpretation before solving
any recurrence. Independently prepare a material-sensitive action-choice test;
semantic fidelity, construction motivation and deployment evidence remain
separate obligations. No dot approval or full WDL calibration is required.
