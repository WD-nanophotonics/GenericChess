# A cheap exact certificate for shared-parameter minimax margins

Let A(h)=min_i a_i(h) and B(h)=min_j b_j(h), with affine leaves and ONE shared
parameter vector h in a closed box. At each h,
A(h)-B(h)=min_i max_j (a_i(h)-b_j(h)). For each i choose nonnegative rational
weights lambda_ij summing to1. A maximum is at least its weighted average,
so min_box sum_j lambda_ij*(a_i-b_j) is a valid lower bound for that row.
Take the minimum of these row bounds to certify A-B throughout the box.
Each affine box minimum is exact, picking endpoints by the coefficient sign.
No parameter is chosen independently at different leaves.

The optimal row certificate corresponds to a small epigraph LP; verifying a
supplied rational combination needs no solver or floating tolerance. This
connection uses the standard epigraph treatment of maxima of affine functions.
[Boyd/Vandenberghe, Convex Optimization, sec4.2/4.3](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf).
The application to shared material-tree differences and its proof above are
local derivations, not a claim of game-value calibration from that book.

## Decision-changing negative control

A(h)=0 and B(h)=min(h,1-h) tie at both box corners, while A-B=-1/2 at h=1/2.
Thus corner checks cannot certify universal choice after defender minimization.
The equal mixture of B's two rows gives a constant lower bound-1/2; the interior
witness makes that bound sharp. This is a precise failure of a proposed cheap
shortcut, not a game result or a new material coefficient.

## Reused actual Shogi leaf table

The complete43 exposed leaf states, frozen board integers/100000 and shared
hP,hR in[0,1] produce190 candidate/baseline row-pair terms. One-hot baseline
certificates verify that the old promoted capture's margin is positive against
each other root action over the whole continuous box. The new verifier does
not assume each branch minimum is globally represented by one affine leaf:
that fact is explicitly checked for this table before choosing its one-hot
certificate. The switching control exercises a genuine multi-row certificate.

This qualifies a more general arithmetic boundary for future complete depth2
trees. It does not add a production run, strengthen the old goal evidence,
choose a hand price, qualify full-stock captures, or establish a useful prior.
Evidence: `data/shared_min_envelopes_20261006.json`, frozen protocol/producer.
Recorded time0.015sec; zero public transitions, runtime pushes/source queries.
Seven exact-certificate tests pass. Incomplete/forged distributions, floats and
dimension errors fail closed. Deeper alternating backups need a separate
piecewise structure argument; do not extend this min-envelope interface by
assuming an arbitrary backed-up score remains affine or concave.

Root orientation is caller-owned: first express all leaves in the ROOT player's
orientation, then the opponent is a minimizer for either physical owner. A
lower score margin is not a goal/WDL margin. Tie-breaking needs its own strict
or canonical-order condition and is not implied by a nonnegative weak bound.
