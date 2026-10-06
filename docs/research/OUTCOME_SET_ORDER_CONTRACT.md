# Complete outcome-set order contract

Dot suggested keeping material outcome sets rather than a chosen scalar label.
For complete finite X,Y in the same integer feature space and perspective,
certify C(X,Y): every x in X has some y in Y with x>=y coordinatewise.
For any shared coordinatewise nondecreasing utility u:
u(x)>=u(y)>=min_Y u. Taking min_X proves min_X u>=min_Y u.
This includes common nonnegative linear prices, but not negative prices or
different utilities in the two branches. No strict gain follows for all
nonnegative weights, since zero weights are allowed.

This is also necessary if ALL isotone utilities are allowed on the full
finite feature domain: if some x0 has no y<=x0, choose the isotone utility
u(z)=1 iff at least one y in Y satisfies y<=z, otherwise0. All Y have value1,
x0 has0, so the worst-case order fails. This indicator proof is local, not
a theorem imported from a sequential-decision paper. It need not be necessary
for a restricted LINEAR class: X={(1,1)},Y={(2,0),(0,2)} satisfies every
nonnegative linear worst-case order, yet no individual y lies below x.
Convex witnesses could strengthen that restricted class, but would not prove
the nonlinear class, physical outcome occurrence or a mixed opponent policy.

Keep all action-to-vector incidence. Coordinate-minimum vectors may be
unattainable; Pareto-worst outcomes can compress a scalar lower envelope only
after completeness and the same utility have been specified. Repeated vectors
may share arithmetic storage, never state/history/legal-action certificates.
Mixed real terminal classes must be kept separate; no universal material
weight claim across a WIN/LOSS boundary. Empty or incomplete outcome sets
cannot prove anything. Candidate root ties require separately proving order
for every permitted controller, not choosing a favorable tie after labels.

scripts/outcome_set_order.py is a sufficient finite set verifier, NOT a search
algorithm or production pruning adapter. Its caller must establish complete
policy/defender outcomes, common horizons and full rule semantics. Exhaustive
tests check225 set pairs against all isotone Boolean utilities on the two-bit
cube, plus linear-converse and incompatible-minimum controls. This contract
does not identify the right Chess prices, model eventual WDL, or validate a
heuristic against the leaves it already optimized.
