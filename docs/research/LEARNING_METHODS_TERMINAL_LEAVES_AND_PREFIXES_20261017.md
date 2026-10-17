# Learning methods, terminal PV leaves and prefix exposure — 2026-10-17

Science OPEN. Keep TD as a cheap retained comparison; these results do not select
a universal learning method or stable generic prices. PRIMARY read and executed
published AUX88 evidence, then found and repaired a separate CURRENT PRIMARY
terminal-leaf defect. AUX's checkout, producer, weights and frozen caps are untouched.

## Current PRIMARY correction

A real rule with max_ply=1 and an extra owner-0 rook reaches a scoring draw after
one legal move. Both ordinary Native and semantic Native return a completed PV
ending there. The old collector recorded tanh(material/scale), not the terminal
constant0; the trainer differentiated that material vector. This is a different
defect from the preceding RESTART/NO_CONTEST-as-draw repair.

TrainingPoint now has an optional leaf_terminal_z. Collection obtains it from the
FULL replayed Core GameState, stores0/+1/-1 for scoring terminal leaves, and keeps
all original board/hand/dynamic features and histories. Non-scoring PV leaves
raise explicitly. The trainer treats marked leaves as constants: their own
gradient is zero, while previous eligibility decays normally and may still receive
later credit. Terminal draw constants also have zero derivative, despite tanh'(0)
being nonzero. Actual episode outcome and a counterfactual terminal PV can differ
after exploration; neither is substituted for the other.

The field is emitted ONLY when present. Old records remain readable and their
current payload/ID is unchanged. They retain their historical feature contract:
missing terminal metadata cannot be reconstructed from a key alone, and this
change does not relabel old archives. New terminal-annotated trajectories naturally
have different IDs. No search/evaluator/default, learner algorithm family, rule,
Native binary or AUX implementation changed.

The first complete regression found an affected real consumer:
td_signal_diagnostics still differentiated the old material prediction. Its
existing material-only instrumentation now follows the same terminal-constant
contract and rejects empty non-scoring episodes too. The initial failure and
intermediate source qualification are retained; they are not called passing runs.
This does not expand that diagnostic into a general dynamic/spatial trainer.

Final16 targeted cases cover actual ordinary/semantic Native draw PVs, actual
automatic NO_CONTEST refusal, zero terminal derivatives for all three scoring
values, prior eligibility at lambda0/.7/1, invalid constants, serialization/legacy
IDs and the diagnostic consumer. The original9-case run had8 failures/1pass before
the correction. Final isolated Python-only16-case red/green has12fail/1pass/3Native
skips before versus13pass/3skips after. The3 Native cases execute in the normal
PRIMARY environment. Final3259 complete checks and56related checks pass. The initially failing
instrumentation case passes after correction. [Qualification](../archive/learning_methods_terminal_prefix_20261017/qualification.json)
keeps full, publisher, normal Native and isolated-source tiers separate.

## AUX88: actual evidence and independent scope

Pinned source:
[3f9afcc3f5d5cca722eda64c305d542a5b168203](https://github.com/WD-nanophotonics/GenericChess/tree/3f9afcc3f5d5cca722eda64c305d542a5b168203).
The [owner report](https://github.com/WD-nanophotonics/GenericChess/blob/3f9afcc3f5d5cca722eda64c305d542a5b168203/results/dev_aux/SEGMENT_20261017_88.md)
and corrected fresh-entry instructions were read. PRIMARY checked all197 capsule
payload hashes, supplied the single exact87 DATA fixture explicitly documented by
the owner, executed36 owner-authored tests and regenerated seven sealed A/B audits.
Old derived outputs were removed before recomputation; all fields except audit
wall time agree, in35.656s. This executes owner-authored checks; it is not a claim
that PRIMARY wrote them or used an independent rules implementation.

The original88 archive is18,295,913bytes, SHA256
1375cf3eb50a2818407791cfb32bb0d142daa1b77e7abaf0c36c8bbcfcf88717.
The inherited fixture is task2505/queries.jsonl, SHA256
6c49693f460e34abee981654e038f18583b7216d1ce7a88a31a55ac019a95aba,
from the unchanged87 archive. The first owner's35pass/1missing-fixture run remains
a transport failure; neither its archive nor any experiment was silently repaired.

PRIMARY separately authored scalar gradient geometry and paired-outcome arithmetic.
All960 actual game records retain952 actual terminals/8H512UNKNOWN; no missing
evaluation slots. All711 training episodes and12M attempted nodes remain. The
seven recorded original producers cost26,921,851nodes/3615.505s, excluding engineering,
audits and delivery. No new training/game producer reproduces that cost here.

|Panel|Actual terminal / UNKNOWN|TD or Root minus initial|Tree minus initial|Direct Tree minus comparator|
|---|---:|---|---|---|
|A endpoint,16families|382 /2|[.40625,.4375]|[.2734375,.2890625]|[-.1484375,-.1328125]|
|A midpoint,8different families|189 /3|[.25,.28125]|[.109375,.171875]|[-.171875,-.078125]|
|A different foe,8matched endpoint families|189 /3|[.25,.34375]|[.21875,.25]|[-.09375,-.03125]|
|B endpoint,8new families|192 /0|Root+.125|+.109375|Tree−Root−.015625|

These are paired W-L reward differences, with each unresolved reward in[-1,+1].
The shared initial baseline cancels in direct method contrasts. It is physically
paid once per panel/foe, not counted as independent evidence for each method.

A's four initializations all have positive finite-endpoint gain bounds for both
methods. PRIMARY's independently implemented20,000-replicate crossed seed/family
descriptive envelope for Tree−TD is[-.3984375,.1796875], including zero. Its RNG and
replicate count differ from the owner's5,000-replicate result; small endpoint
differences are Monte Carlo conventions, not a disagreement about actual outcomes.
B's corresponding Tree−Root envelope is[-.09375,0]. B's direct deficit is confined
to one initialization; other initializations include zero/negative absolute gains.
There is no general method winner, equivalence, paired A learning curve or
cross-rule strength inference.

A compares whole regimes: episode-frozen TD sums versus per-search mean Tree
updates, with different targets, frequencies and on-policy data. B aligns update
timing/type and calibrates ONE initial TRAIN-only factor1.4117239536061434 across
all seeds/zeros. Later actual Root update RMS is1.50–1.70times Tree. Neither study
isolates a pure benefit of internal-node information.

## Extra nodes change gradient directions, but usefulness remains unproved

PRIMARY recomputed static half-squared transformed interval semi-gradients without
importing the learner. Targets stay detached; the mean denominator includes ALL
returned interior nodes. The fixed pawn derivative is zero. Every recorded actual
A/B Tree/Root update agrees.

On128 initial64-ply TRAIN trees,52 have zero Root direction but nonzero Tree
direction;40 have both directions nonzero and noncollinear. Per-seed fractions
of Tree gradient energy outside the Root span are.3393/.7538/.3575/.4533.
Thus a single scalar cannot generally convert one into the other. Initial Tree
directions have observed rank4 in all four seeds; that is not unique price
identification or independent sample coverage. On evolving A Tree trajectories
the outside-root fractions are.0701–.2025, on B Tree.0912–.1919; these are different
changing distributions, not a causal before/after comparison.

Nonzero/active counts use explicit1e-14 tolerances; orthogonality uses relative
energy1e-12. The first centered finite-difference step1e-6 failed a1e-9 tolerance
near one-sided-bound joins. Squared hinge loss is C1, with a second-derivative
jump there; the1e-8-step controls pass. Original failed preparation/NumPy JSON
versions are retained privately, not numerical observations or security blocks.

The old exposed87 initial pilot also has nonzero Root RMS in all four seeds,
separately for plain/q2 targets. Earlier eight zero-root examples were valid
local examples, not a general calibration obstruction. No old data fitted a new
learning rate, no unchanged48,017-query replay was repeated, and no extra learner
or Root/Tree training batch was launched.

## Prefix length changes exposure AND the represented distribution

The SAME32 recorded Chess paths from the initial TRAIN calibration were inspected
at16/32/64 plies. Across seeds these are32boards repeated, not128independent
families. Nonzero free N/B/R/Q inputs are3/20/28; observed feature ranks2/4/4.
At64 one path is already terminal and two contain promoted pieces. This supports
an exposure question, not a stronger learner or unbiased full-game price estimate.

PRIMARY then registered72 NEW generated-rule slots: boards4/6/8 × all three
existing setup presets ×8fixed seeds, hybrid movement, ordinary promotion/drop
rules, full Core GameSession state/history. Uniform typed legal-action BINDINGS
define the continuation policy. No opening-quality filter, domain simplification,
search, learning or reward-based selection is added. max_generation_attempts=32
and aggregate1200s stay frozen. One preparation failure at0actions is retained;
the corrected run completes all72slots/3279actions in14.625s.

|Board|Planned rules|Ongoing at16|Nonzero free input at16|Ongoing at64|Nonzero free input at64|
|---|---:|---:|---:|---:|---:|
|4|24|19|19|12|12|
|6|24|18|18|13|13|
|8|24|18|15|16|16|
|Total|72|55|52|41|41|

Terminal-before-prefix cases remain absent; they are not padded absorbing draws
or silently dropped from the72-rule denominator. The executed paths contain817
drops and185promotion actions. A later start can increase conditional signal while
losing usable rules:52 nonzero ongoing16-ply starts versus41 at64 here. A short
chosen random line does not prove a rule unplayable. No rule is rejected.

All3279transitions/3351states were subsequently replayed through complete Core;
saved checkpoints, records and full histories agree. This qualifies this scoped
generator diagnostic, not the complete recombined/auxiliary-rule domain or a
Generic learning result. A future sampler must declare the rule/start-state
measure and treatment of early terminals; do not universally replace16 by64.

## Original sources: what is useful and what is deferred

[Buro, From Simple Features to Sophisticated Evaluation Functions](https://skatgame.net/mburo/ps/pattern.pdf),
all10pages visually checked because the embedded text encoding is unreliable:
Boolean configurations provide sparse interaction features with a linear scoring
core. Sample representativeness, accurate labels, feature frequency and runtime
cost are distinct. The Othello application uses substantial data and
game-informed atomic features; it is not an unknown-rule or small-training
guarantee. Its speed/strength tradeoff supports retaining cheap baselines and
testing a small interaction only for a concrete use. No feature generator/table
learner is implemented here.

[Clune, Heuristic Evaluation Functions for General Game Playing](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf),
pp2–6: rule-derived candidates feed payoff/control/termination abstractions.
Temporal feature stability is an observed variance ratio, not payoff importance.
Its exact abstract model does not solve the original game. Its Chess description
omits ordinary threefold repetition, using a move cap; copying that reduced task
would violate this project's target. No pseudo-state payoff fitter, GDL parser,
abstract solver or imported coefficients follows.

[Schiffel and Thielscher, Fluxplayer](https://cdn.aaai.org/AAAI/2007/AAAI07-189.pdf),
pp2–6: rule-derived goal/termination heuristics are a possible inexpensive
alternative to learning, but formula encoding and evaluation cost matter. The
paper explicitly admits syntactic sensitivity and weak discrimination for some
goals; its tournament evidence is not controlled evidence for our domains.
Adopt those limitations in future designs, not its whole architecture.

As a bounded feasibility check of Clune's statistic, PRIMARY computes overall
population variance divided by mean adjacent squared change on ALL72closed paths.
Constant features have an explicit undefined quotient. Monotone ply is a negative
control: high temporal stability can arise mechanically without identifying a
useful piece price. No feature is selected or fitted. Original Shogi chapter/thesis
retrieval returned HTML,403/404/429; bounded attempts are retained, and abstracts
are NOT treated as read full methods. No access control is bypassed.

## Next decision and reproducibility

Keep the cheap TD comparison and leave AUX's richer TRAIN-exposure test in its
own lane. PRIMARY's next useful consumer question is how a prospective Generic
start-state sampler preserves early-terminal rules and genuine hand/promotion
exposure at bounded total cost. No new cohort is automatically required. Current
terminal-leaf correction is delivered before using this collector for new training.

The companion data and evidence archive retain plans, complete72rule definitions,
typed action journals/full records, independent scripts/results, current source
snapshots and the old-source counterexample. The immutable88/87 public archives
are explicit external inputs; raw Slack/account output, personal paths, credentials
and copyrighted PDFs remain private. Source-copy qualification, normal Native
execution, full regression and publication tests are separate evidence tiers.


[Complete paired data](data/learning_methods_prefix_20261017.json) and
[exact evidence/dependency instructions](../archive/learning_methods_terminal_prefix_20261017/README.md).
