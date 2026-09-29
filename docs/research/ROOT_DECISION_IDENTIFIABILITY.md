# Root decision regret does not identify a static material scale

**Unknown.** If the context is fixed to one declared initial root, the search
cutoff is fixed, and every root action has an exact terminal W/D/L label, does
minimizing root decision regret identify a static material prior?

**Smallest direct observation.** Consider a finite two-action zero-sum game.
At the declared search cutoff, action `g` has leaf inventory `(n_A,n_B)=(1,0)`
and action `b` has `(0,1)`. Each leaf has a forced legal continuation, with
exact terminal outcomes Win for `g` and Loss for `b` from the root player's
view. Thus the root and both labels are fixed; there is no context sampling,
counterfactual piece removal, human value reference, or holdout inspection.

Let the cutoff evaluator be `E(s)=w_A n_A(s)+w_B n_B(s)`, with positive
coefficients and a fixed tie policy. The bounded search chooses `g` whenever
`w_A>w_B`. Its exact W/D/L decision regret is then zero. Every pair in that
open half-plane is equally good under this objective. For example `(2,1)` and
`(100,1)` give the same correct decision but radically different ratios.
Multiplying either pair by any positive constant preserves every leaf order
and therefore every pure material minimax decision at the declared cutoff.
Even imposing `w_A+w_B=1` leaves the whole interval `w_A>1/2` admissible.

This is a direct analytic check: `E(g)=w_A`, `E(b)=w_B`; the true outcome
ordering is `g>b`. It needs no search budget. It does not claim that every
game or richer set of labelled roots is uninformative. It shows that even a
fully labelled, initial-root, fixed-depth decision-loss experiment need not
identify a cardinal material vector. Further labelled roots could constrain
ratios, but pure material decision comparisons remain invariant under common
positive scaling. A numerical mate score, regression target, margin, norm, or
reference-piece unit can break that invariance only as an *additional* scale
convention or objective; rule legality and ordinal W/D/L alone do not choose
one. Search implementations that mix material with fixed numerical nonmaterial
terms also import those terms' units, so the scaling statement applies to the
declared pure-material experiment rather than silently to every engine.

**Decision.** Keep root regret as a validation objective for a *frozen* prior,
not a derivation of its cardinal values. The prior still needs an independent
game-independent comparison and unit principle. The next bounded route is to
inspect whether a rule-derived resource conversion supplies such a unit across
Chess and Shogi. State the conversion operation and its invariance conditions
before measuring values; reject it if capture, promotion, or hand transfer
changes what is being exchanged. Do not tune against the labelled Chess mate
fixtures or inspect Xiangqi material values.
