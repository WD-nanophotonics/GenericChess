# Conditional horse connectivity through local detours

The frozen record qualifies a sufficient subset of the virtual9x10 contact
worlds. It does not solve the remaining complement or independently qualify
the full compiled H distance histogram. Both own blocker B and enemy target T
block legs until capture; target-free ordinary Knight distances are not H distances.

## Construction and assumptions

[Schwenk's1991 theorem](https://www.math.cmu.edu/~nkomarov/21-110/knighttour.pdf)
admits a closed ordinary Knight tour on9x10. Removing B from its Hamiltonian
cycle leaves a spanning path through the other89 squares. Its S-to-T subpath
has at most88 edges. We use this published existence theorem; no local tour
witness or exhaustive graph search was generated.

An ordinary edge blocked by a leg O has one of eight directed orientations.
For O=(0,0), the canonical edge(-1,0)->(1,1) has the detour
(-1,0)->(0,-2)->(2,-1)->(1,1). Its legs are
(-1,-1),(1,-2),(2,0). The frozen independent coordinate check verifies all
eight orientations,24 edges: no landing/leg is O and all are within radius2.

Require B and T each at least2 squares from every board boundary and
Chebyshev distance(B,T)>=3. Then each detour stays on board and avoids the
other occupied center, for both landings and legs. Replace every original
edge blocked by B or T. Original path landings already avoid B; it ends at
the first T. Inserted detours also avoid both centers, so cannot arrive at T
early. Final incoming leg is never T; separation excludes B from that leg.
The resulting directed walk is a legal H contact path. Repeated intermediate
vertices are harmless in this virtual stationary-occupant contact model;
no official repetition-goal or alternating-game claim follows.

A fixed occupied center blocks at most8 directed ordinary edges: four adjacent
origins and two destinations per origin. A simple original subpath can use
at most these8, hence at most16 replacements for B and T combined. Each adds
two steps, giving the loose sufficient bound88+2*16=120. Removing loops could
only shorten it, but no exact distance is claimed.

## Scope, cost and mainline impact

Interior centers lie in a5x6 rectangle. Ordered pairs with separation>=3
number30^2-19*24=444. With88 allowable origins each,39072 of704880 worlds,
mass74/1335, have contact time<=120 under the stated virtual semantics.
The displacement calculation and stencils cost34 new analytic terms:
cumulative4994/5000, forward nodes remain1579. Zero public state transitions,
compiled queries, slab queries or new graph census. Only6 analytical terms
remain in this existing H budget; no reset is authorized.

This is constructive connectivity evidence for one nonempty subset. It is
not independent deployment usefulness, a refined complete H distribution,
or proof that400 known unreachable worlds are the only failures. Short-time
tau1/tau2 certificates can overlap this subset; never add its39072 worlds to
those masses without a disjointness certificate. The standalone lower mass
also does not improve their already larger aggregate prefix lower bound.
The next useful deployment direction is prospectively qualifying an outcome
reference for the richer controller, rather than spending the last6 terms
on a broad H census.

Frozen evidence: HORSE_INTERIOR_DETOUR_PROTOCOL.md,
data/horse_interior_detour_20261006.json, scripts/audit_horse_interior_detour.py.
The external ordinary-tour premise and the locally checked H detours are
distinct parts of this argument. Tests validate saved evidence and its
arithmetic; they do not run another world sample or replace the theorem.
