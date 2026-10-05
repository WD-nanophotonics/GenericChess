# Linear decision certificates from physical simulations

The complete Shogi coordinate intervals deliberately retain unknown distances.
Independent box arithmetic may lose valid information: e.g. the TP and native
P intervals overlap, but a same-world path simulation proves wTP-wP>=delta>0.
Do not choose midpoints, invent a Gold/native L relation, or fit to a label.

Let x be the shared-law current-mode raw mean vector in box[l,u]. A proved
physical simulation supplies a_j*x>=d_j. For any nonnegative exact multipliers
lambda_j, define r=c-sum(lambda_j*a_j). Then a sound lower for any material
inventory difference c is

    c*x >= sum(lambda_j*d_j) + sum(r_i*l_i if r_i>=0 else r_i*u_i).

This follows by substitution, not independence of coefficients or a point
price. Taking the maximum with the original box lower cannot weaken evidence.
An upper follows by negating c and the resulting lower. No optimizer is needed
for a useful certificate: an exchange c=eTP-eP uses lambda=1 on its physical
constraint. Joint TP+L-2P uses both named constraints simultaneously. Shared P
is NOT duplicated independent randomness. Current G/TP/TL/TN/TS equality may
first identify coordinates; native S/N/L remain distinct.

Multipliers are algebraic proof witnesses, not fitted coefficients. A missing
proof or negative multiplier is rejected. A bound need not be tight; failure
to certify is not a counterexample. Existing compiler/input/promotion/path
scope remains necessary and no actual gameplay improvement is inferred.

Both predeclared duration laws must retain their OWN boxes and deltas; never
combine a half box with a mixture constraint. For pure linear material choices,
positive common scaling preserves signs, so arbitrary Shogi max normalization
is unnecessary. Terminal priorities/full-child eligibility remain a separate
interface obligation. No old frozen selector or use evidence is changed.
