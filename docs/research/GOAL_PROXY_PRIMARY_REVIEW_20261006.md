# Primary-source review: evaluation information versus surrogate preference

This review changes the next experimental contract rather than selecting a
price or expanding an old tree. Local saved results remain independently
reproduced mechanics, stable static order and negative short-window gain.

[Tzeng and Purdom1983, A Theory of Game Trees](https://cdn.aaai.org/AAAI/1983/AAAI83-080.pdf)
models binary game outcomes and conditional forced-win estimates with nested
search information. Its product backup requires conditional independence;
correlated game models are outside that premise. My corresponding inference:
for fixed bounded outcomes Y_i and nested information F subset G,
E[max_i E[Y_i|G]|F]>=max_i E[Y_i|F]. This follows from conditional Jensen,
not from treating any static material score as a calibrated conditional value.
Our cutoff window and eventual utility are different targets, so deeper
material minimax is not automatically a martingale improvement. Approximate
constructors remain worth testing; this theorem is not their admission gate.

[Delcher and Kasif1992](https://cdn.aaai.org/AAAI/1992/AAAI92-079.pdf)
combine evidence at multiple depths using a probabilistic belief model that
needs suitable priors and conditional error rates. Their tested heuristic is
domain-specific. This does not supply calibration-free generic contact prices
or free full-tree computation. Keep model, estimator and measured decision
quality separate instead of importing their improvement conclusion.

[Muller1999, Partial Order Evaluation in Game Tree Search](https://cdn.aaai.org/Symposia/Spring/1999/SS-99-07/SS99-07-018.pdf)
uses domain partial orders to answer success-bound queries with WIN/LOSS/
UNKNOWN, including restricted Go examples. Unknown comparisons remain unknown.
Its application-specific bounds are not our coefficient-domain search window
or a complete material-to-goal bridge. Local set and polynomial certificates
can support ordering or exact pruning only under their own proved premises.

[Clune2007, Heuristic Evaluation Functions for General Game Playing](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf)
extracts payoff, control and termination abstractions and evaluates their
stability from simulated states. Its payoff abstractions depend on the game's
goal; the illustrated cylinder-checkers count target is not ordinary Chess
winning. Sampled control/termination models and compound evaluation therefore
cannot be substituted by uncalibrated contact sums. We can borrow the explicit
goal/dependency audit idea without fitting exposed labels or copying weights.

[Roijers et al.2013](https://www.cs.ox.ac.uk/people/shimon.whiteson/pubs/roijersjair13.pdf)
defines strict monotone scalarization and Pareto dominance in4.2.2 and permits
unresolved tradeoffs without preference information. This supports preserving
vectors, while our adversarial set theorem is an independent derivation.
Its MOMDP taxonomy is not a ready-made Chess exchange experiment.

Chosen next direction: a prospective first-quiet exchange proxy with genuine
captures/quiet actions and full correlated outcome sets. It may falsify resource
nondegradation, but cannot identify cross-type prices or eventual WDL. New
information must lie beyond the frozen controller's own scored frontier;
otherwise order is largely restating optimization. This segment's first such
pilot failed ROOT ADMISSION at128 proposals, with0 transitions and no labels.
Future selection should inspect recapture feasibility and the tree-cost
representation BEFORE price disagreement/outcomes, not rescue that failure.
The advisor's independent proposal and limitations are reviewed separately in
ADVISOR_20261006_1026_REVIEW.md. No worker or extra source acquisition.
