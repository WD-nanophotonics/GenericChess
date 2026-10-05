# Shared coefficient uncertainty after a defender minimization

Question: can a complete depth2 material tree preserve one shared held vector
without sampling corners or choosing a hand price? For a fixed root action,
the opponent backup is the minimum of finitely many affine leaf scores.
Two such minima need not have an affine difference; box corners alone do not
certify universal choice. Do not independently choose hand parameters per leaf.

New exact-arithmetic verifier accepts affine rows, exact box bounds, and for
each candidate row a nonnegative rational convex combination of baseline rows.
It certifies a lower bound on the difference of the two min envelopes using
max >= convex combination and the exact box minimum of that affine combination.
This is certificate CHECKING, not coefficient fitting or numerical optimization.
One primal witness may show a bound is sharp; it cannot certify the whole box.
Row provenance and complete legal tree remain caller-owned qualifications.

Frozen control: A(h)=0, B(h)=min(h,1-h), h in[0,1]. Both corners tie, but B
strictly beats A inside. Equal convex weights certify A-B>=-1/2, with equality
at h=1/2. This directly falsifies a proposed corner-only material-tree shortcut.

Reuse the43 exposed Shogi leaf records only as an arithmetic/control input.
Take the already frozen board integers/100000, with shared hP,hR in[0,1].
For each complete branch, derive its affine leaf rows. A known globally minimal
baseline leaf supplies a one-hot certificate against the promoted-capture
candidate. No new production run, position/root selection, game observation,
source query, holdout read, coefficient selection or old-window deepening.
Cap64 total leaf rows,7 dimensions,4096 row-pair terms,15sec. Persist failures;
do not install an LP package or enlarge this budget. This qualifies a more
general checking interface, not full-stock deployment or WDL improvement.
