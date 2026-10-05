# Shared duration-law and held-price uncertainty in the saved complete tree

Prospective question: does the already selected promoted-capture branch remain
strictly preferred when the WHOLE tree shares an unknown convex mixture of
the two frozen duration mechanisms, as well as unknown held-P/R prices?
This is conditional uncertainty analysis, not a third admitted prior or fit.
Use only the saved48-event/43-leaf Shogi promotion tree; no event expansion,
goal labels, human references, new root, duration choice or held-price choice.
Candidate fixed legacy_029:g21:a7-a8=TP BEFORE arithmetic.

Let alpha weight geometric_half versus linear_mixture, alpha in[0,1]. Raw
board means and common TR denominator are affine in alpha. Normalize every
board term by that ONE denominator. Held-P/R coefficients hP,hR in[0,1] are
already normalized. Thus each leaf score numerator is a multiaffine polynomial
in alpha,hP,hR: board(alpha)+TR(alpha)*(nP*hP+nR*hR). TR is strictly positive.
Do not replace shared normalized coefficients by independent interval choices.

For a supplied convex combination of baseline leaf polynomials, each candidate
leaf minus that combination lower-bounds max baseline-difference. A multiaffine
polynomial on a box is a convex interpolation of its vertex values, so its
minimum is attained at a vertex. This justifies checking the CERTIFICATE
polynomial vertices, not sampling the backed-up min envelopes' corners.
The earlier switching-envelope counterexample must still fail naive corners.

Protocol seeks a baseline leaf globally minimal on the entire box by exact
pair polynomial vertex bounds, then supplies a one-hot combination per
candidate row. Failure to find such a leaf is inconclusive; no adaptive solver,
extra leaf, sampled fallback or tuned coefficients. Also derive exact S/C
mixture crossover from the new independent diagnostic means; no law chosen.

Budget64 saved leaf rows,4096 pair-vertex evaluations,15sec,0 game/state
transition/geometry/source query. Preserve partial/failure evidence, no reset
or larger tree. Exact rational coefficients, dimensions3/eight monomials only.
Store full rows/proofs and source pins. Static dominance is not mate/WDL,
independent strength or product interval-search integration.
