# Finite-search compression development target

This is an offline decision/cost study with one small trained prototype, not true value,
WDL calibration, player strength or unknown-rule transfer. Keep static prices
as controls; no product default, history key or legality guard changed.

## Decision and frozen population

The next useful question is whether a cheap state predictor can preserve a
finite search's root decisions. Root regret, all legal alternatives and actual
cost matter more than sibling-pair accuracy. In the older135child population,
unit-material greedy uniform ties incur teacher regret1846.15/0/0/666.67 across
four roots. Two roots need no correction. Relative-pair and Position-plus-pair
inputs have no collisions or equal-sum revisits in9180unordered input pairs;
that absence does not establish learning or generalization.

Six new legal trajectories were frozen before teacher generation, using the
already exposed generated RuleSet202610082102. Seeds2026100902–0907 each reach
ply8; all27/45/46/44/29/37legal children are retained. Whole trajectories were
assigned two each to prospective train/development/report groups. Exact Position
hash overlap between groups is zero; sibling/trajectory dependence remains.
These are not independent unknown-rule holdouts. Aggregate report labels have
subsequently been inspected; no strict unexposed-test claim is available.

The teacher is owner0 unit-material minimax with remainingD2, q0, complete
GameState/history, Core, no TT/order/disk/root tactics. Each D2 call has the same
2048node/1second condition. All228complete, totaling48.81seconds/79257nodes.
No terminal-derived target occurs: the returned scores lie between−2000 and4000.
The producer's coarse terminal threshold is not a general mate classifier;
it makes no classification difference in this population.

An optional D4 arm used20000nodes/5seconds per child. Its first55calls all cap
after completedD3, costing274.83seconds/432242nodes. The arm was stopped for
poor incremental information per cost;173children were never attempted.
All228declared D4 targets remain UNKNOWN. The saved partial is immutable.
One fully covered root's posthoc D3 child scores retain the D2-best choices;
that is one diagnostic, not six-root stability or a completed D4 experiment.
Dot's reviewed recommendation is to retain the scoped D2 compression target,
without making deeper qualification a prerequisite.

|Trajectory suffix|Children|Unit-greedy expected D2-child teacher regret|
|---|---:|---:|
|0902|27|1666.67|
|0903|45|0|
|0904|46|2000|
|0905|44|0|
|0906|29|0|
|0907|37|2000|

Equal-root regret is944.44 versus1399.69 for blind uniform action selection.
Units are the fixed teacher's1000per ordinary piece, not money or true utility.
Full material vectors, unlike their scalar unit sum, are distinct input groups.
A descriptive clairvoyant material-group selector has minimum uniform-tie
regret400 and1125 on0904/0907, zero on the other four roots. It may choose a
different group at each root and is more flexible than shared static prices;
no coefficients were fitted. This bounds a greedy material-only scorer with
state-independent uniform ties, not a material evaluator combined with search.

## Existing search is an essential cost control

Forty-eight baseline calls compare whole-root D3/20000nodes at.1/.3/1/3seconds,
two balanced repeats on all six roots. The12three-second cells completeD3 with
zero teacher regret and mean actual wall1.804seconds. The shorter cells retain
every cap: completed depths1/2/2 and mean regret1000/666.67/666.67.
Root D3 and complete child D2 agree here; this does not certify true values.

Another48balanced full-D3 calls compare existing TT and ordering switches.
All complete with zero teacher regret. Median per-root wall ratios versus
neither switch are1.026(TT),.694(order),.700(both). Ordering reduces work;
this is not a price or learning gain. No default switch changed.

At the same1second budget, a separate48calls expose an adverse result:
baseline/TT mean regret666.67, ordering/both1000. Ordering completesD3 on one
already zero-regret root but changes another root's completed-D2 tie choice
from teacher regret0 to2000. Faster completion is not automatically better
finite-budget selection. Two order-balanced repeats retain the same choices.

A smaller independent full-width D1-child reference covers only0904/0907,
83children, whole-batch10second/4096leaf safety fuse; it finishes in about1second.
Their root D2 best sets contain34/22actions. Every compared D2 selection is in
the correct best set; uniform-tie D3 regrets are117.65/454.55. Thus the adverse
choice is a shorter-horizon tie effect, not a proven search-value error.
The initially proposed228child per-reference-cap run was rejected before
execution by automatic approval review; the reduced bounded run is retained.

An unchanged-guard timing probe across six completeD3 searches records19627
legal membership checks: only.34–.65percent of wall time. Defer a new dict/set
optimization. Four original complete generated-rule openings are also safe,
ongoing, with48/46/26/34actions and no immediate terminal action; this small
negative control does not justify another filtering framework. Neither control
proves complete-domain playability or cancellation behavior.

Two existing rule-generated material-only tables remain explicit controls,
with dynamic mobility/anchor/promotion bonuses disabled. Their all228child
value arrays coincide in this cohort; greedy mean unit-teacher regret666.67
differs from unit-greedy944.44. That is agreement with a unit teacher, not
independent utility. Twenty of24balanced three-second D3 callers complete;
both repeats of both tables cap at0905, where unit completes. The mean
unit-teacher regret333.33 includes those caps. Price-dependent tree work must
stay visible in the later deployment comparison. Neither table was tuned,
removed, promoted or declared better by this diagnostic.

## Single fixed predictor and actual caller

The concrete pilot uses SparsePositionEncoder with1682channels and explicit
history omission. It retains current/base/promoted actors, hands, side and aux;
full history remains in teacher/search. Train72children, development90,
report66. Of1682channels,159vary in training;79/56additional channels differ
from the training-constant support in development/report. This is distribution
diagnosis, not a model-selection threshold or evidence of independence.

Target: owner0 V_D2(child) minus owner0 current unit material. Add the material
baseline back before owner0 maximization or owner1 minimization; successor-root-Q
is a different contract. Do not silently bind this offline input to the older
Native model schema. Primary measure is complete-root teacher regret with
uniform exact prediction ties; MSE is diagnostic. A trained leaf inserted into
deeper search would be a new algorithm requiring actual caller measurement.

One prepared existing width16 residual fit has fixed seed2026100916,
regularization.0001,600epochs, learning rate.01, train-only normalization and
a120second CPU safety checkpoint, no sweep/restart/extra worker. The default
runner only checks inputs and exits PREPARED_NOT_STARTED. The explicit execution
flag was used once after user2026-10-09 authorization for appropriate small local
training. Single runs expected to exceed one hour first require consultation
with dot about necessity; see LOCAL_AGENT.md Budget. This fit took0.514seconds,
saved895871bytes and predicted the228child batch in0.00333seconds.

Training-root mean teacher regret is0, versus833.33 for unit greedy. Development
and report means are both1000, identical to their material controls. No retuning,
restarts or report-label fitting followed. Resetting all training-constant
channels to their training means changes predictions by at most2.51e-12 and
changes no chosen action. Their hidden weights are at most3.22e-15 after the
regularized fit; novel-channel counts alone do not explain the observed failure.
This negative result concerns this72sample fixed model, not all learning routes.

A separate actual caller combines the same fixed owner0 residual with material,
then converts to side-to-move perspective. Twenty-four balanced one-second
Core calls compare unit versus learned leaves on the six roots, with identical
D3/20000node/q0/no-TT/no-order conditions. All stop after completedD2. Unit mean
teacher regret is666.67; learned is0. This is a different algorithm from greedy
compression, and a scoped comparison with a finite unit teacher, not independent
utility, strength or unseen-rule evidence. Dense learned leaf calls consume
6.106seconds across7915scores versus0.095seconds across17791unit scores.
The batch inference timing therefore understates actual per-leaf costs.

Preconverting fixed arrays and computing only active input contributions agrees
with all228dense predictions within1e-9. Another24balanced one-second calls
retain the same zero learned regret and allD2completion, with0.554seconds for
19154leaf calls (28.94microseconds each versus771.5dense). These are scoped
instrumented costs, not a universal speed ratio. A separate three-repeat228row
microcontrol finds cached dense multiplication faster than sparse multiplication
on already-dense inputs; both eliminate repeated tuple-to-array conversion.
It excludes real Position encoding, legality and search. At that checkpoint no
product changed; the cached public implementation below is a later change.

Six additional lexical legal trajectories2026100910–0915 were frozen after
training, before new scores, using the same exposed RuleSet and unchanged model.
The90second whole-run checkpoint covers D3/20000node/3second unit references,
two balanced one-second caller repeats, and selected-child D2/2048node/1second
references. Five root targets and their selected-child references complete:
ten known choices per method, mean regret400(unit) versus0(learned). Root0915's
target is incomplete, leaving two choices per method UNKNOWN; no extension or
shallower substitution. All six declared roots remain in the record. This is
same-rule development evidence, not independent task utility or generic transfer.

At the preceding checkpoint the pure-type-rename control was incomplete. Reusing old public action IDs
fails because legacy geometry/pattern IDs depend on sorted type labels. Full
structural geometry matching can disambiguate identical drop shapes by their
type-associated patterns, but an explicit replacement pattern still references
a legacy ID absent from the active pattern list. The prototype stops there.
No renamed feature/prediction/action invariance has been established, and this
is not evidence of a compiler or learned-model defect: the mechanical mapping
is unfinished. Preserve the failed producers rather than weaken semantic action
identity to coordinate equality. This is a scoped next question, not a new gate
for unrelated small training or useful deployment diagnostics.

The primary [TDLeaf paper, sections4–5](https://arxiv.org/pdf/cs/9901001) updates
evaluation parameters through minimax PV leaves and temporal differences between
searched game states. It reports dependence on initialization and opponent/data
conditions. Our proposed fixed-teacher squared-loss compression is different:
it is not TDLeaf, return learning, or evidence of unknown-rule sample efficiency.
This supports measuring deployment separately rather than claiming that matching
the finite teacher establishes playing benefit.

Exact scripts, declarations, all caps/partials and reproducible summaries:
[compression data index](data/search_compression_20261009.json). Private Slack,
account records, process command lines and live operational state stay local.


## Relabel completion, immutable prediction cache and observed continuations

The subsequent control closes the mechanical rename issue without weakening
semantic action identity. Mapping all lowered legacy patterns first resolves
replacement IDs absent from the active pattern list; full geometry/actor/pattern
mapping retains all228inputs bit-for-bit. Six foreign-layout fingerprint guards
reject accidental rebinding. Twelve actualD2/20000node/5second calls complete;
all six mapped root actions and scores agree. This is pure symbolic equivalence,
not transfer to a new capability, rule distribution or arbitrary tie policy.
The prior failed producers and incomplete-status record remain recoverable.

The public CompactNonlinearResidual now lazily caches five read-only parameter
arrays from immutable tuples. Arithmetic order, checkpoint payload, fitted
weights and numerical output are unchanged: all228batch/individual predictions
are bit-identical. It retains242464additional array bytes for this model.
Twenty-four balanced one-second Core calls preserve every completedD2 action
and score. Legacy8250leaves cost6.136seconds, cached19491cost.682seconds,
743.75 versus35.01microseconds per instrumented leaf including Position input.
The changed node totals include incomplete next-depth work, not stronger choices.
Stored-vector conversion-only timing is separate; no universal speed ratio,
Native change or default evaluator promotion follows.31related regressions pass.

Twelve fixed-model paired continuations from0910–0915 preserve full rules,
auxiliary state and relevant history, with identicalD3/20000node/1second/q0
search conditions and48new-ply censoring. They take584.06seconds: one learned-
owner0 checkmate and eleven ongoing censored games. All565submitted moves and
final states replay exactly; censored outcomes are not draws. At the losing
Unit policy's last move onlyD1had completed. Separate five-secondD2diagnostics
complete for both policies; Unit's new choice avoids the observed drop mate,
and the learned choice makes that specific reply illegal. This checks one
observed threat, not all defenses, and does not attribute the win to learning.
The initial metadata failure after one unrecorded move is retained separately.

## Both-side support and the next conditional input comparison

The original72training children all have side-to-move1. Four declared same-board
fresh-history counterfactual pairs show two2000-point UnitD2differences while
the original predictor is effectively unchanged. These are artificial support
diagnostics, not played states. A new predeclared eight-trajectory7/8ply batch
has308complete child references in80.15seconds. Two fixed width16fits share
154training rows,78/76sides, with identical budgets and train-only normalization;
one uses side channels and one masks them to the train mean. Fits take.437/.536
seconds. Both have zero regret at all eight roots; the four development/report
roots already have zero Unit-greedy regret, so they establish no improvement.
There is no overlap with the original228Position hashes or between new groups;
this does not establish statistical independence or new-rule generalization.

Thirty-two actual one-second callers all completeD2. Unit, new aware and new
blind callers have zero finite-teacher regret; the old72model has2000regret at
0920and zero elsewhere. This does not isolate a causal benefit of side features:
new sample support changed and both new ablations agree. Zero top-choice regret
also hides substantial pair-ranking errors. Five children at0925have forced-mate
teacher scores, making squared-error diagnostics enormous; retain those failures
alongside separately labeled ordinary-score error, rather than changing the
primary metric or silently turning extreme values into draws.

The next comparison follows a focused advisor objection: changing input, data
and loss together cannot identify input usefulness. Freeze whole new trajectories,
complete their legal frontiers, then screen solely by Unit-greedy/teacher choice
disagreement before any candidate prediction. Preserve all zero-disagreement and
UNKNOWN roots. Compare aware Position against that same input plus the retained
mechanical relative-pair histogram under the same fixed, root-weighted bounded-
margin ranking objective. The comparison is conditional on this screening domain;
it cannot establish natural-position improvement. Pure rank scores stay outside
numeric search leaf evaluation. No deeper-teacher certificate, new workflow gate,
report-driven resampling or automatic model promotion is required.


## Frozen conditional ranking result

Twelve new whole trajectories0940–0951, roots at7and16plies, were fixed before
teacher scores. All24legal frontiers/1055childD2references complete in332.66
seconds under the same per-child2048node/1second/q0conditions. Seven roots have
positive uniform material-greedy teacher regret; seventeen have zero. Conditional
selection occurs before any candidate prediction and preserves the full screen.
The whole-trajectory split is6train/3development/3report; selected roots are4/1/2.
This deliberately screened domain is not natural-position or unseen-rule evidence.

Two fixed small linear rank models use the same202training children, all
teacher-optimal versus strictly lower pairs, margin1hinge loss, equal root total
weight,300Adam steps and train-only normalization. Owner0rank is maximized or
minimized by the root actor. Position has310training-variable columns; Position
plus the existing ordered relative-pair histogram has5876. Fits take.036/.525
seconds. A finite-difference check verifies the actual hinge gradient, and four
pair histograms match a separate ordered-pair loop. Pair counts augment the
base/promoted/hand/side/auxiliary input, not replace it; history is still omitted.
All fitted outputs are pure within-root rankings, not calibrated search leaves.

Both inputs achieve zero training-root regret. On the one selected development
root0946/7both have2000regret, worse than material-greedy1000. On report0949/16
both have4000regret versus3561.64material-greedy; on0951/16both achieve0versus
999998000material-greedy. Report those roots separately: a mean dominated by one
mate-scale root would obscure the adverse ordinary-score case. Different actions
can still have identical regret; no extra relative-pair choice benefit is observed.
No restart, sweep, test-driven sampling or default promotion followed.

Sixty-three actual root-only controls regenerate all legal actions/children,
validate complete action identities and preserve the root state. Across three
balanced repetitions on seven roots, material/Position/Position+pairs take
6.952/7.010/7.135seconds total; feature/scoring costs are.008/.037/.158seconds.
Legal generation and full child transitions dominate these simple callers.
A separate, explicitly exposed21call Unit search resource curve uses.2seconds,
the per-root median Position caller budget and1second. At rank-matched budgets,
Unit has zero regret on all three selected development/report roots, where both
rank models have2000/4000/0. Training-root advantages do not establish deployment
benefit. Keep Core as the operational baseline; defer expanding relative pairs.

Post-result algebra decomposes the two retained rank errors into actual current/
base board and pair contributions, preserving promotion action identity. It does
not establish that novel or ignored training-constant channels caused the errors.
The shared record writer now handles already-loaded NumPy scalar metadata without
adding NumPy to stdlib-only consumers; arrays remain explicit NPZ data. Nine
atomicity/type/nonfinite regressions pass. The rank summary failed on a NumPy
string after both models were saved and verified; it was recovered from those
checkpoints without refitting. The original failed producer and exact fit times
remain archived, and the corrected producer refuses an existing-model rerun.

Decision: no relative-pair expansion or rank-model leaf binding is justified by
this batch. Retain the conditional comparison and its adverse outcomes, then
choose a changed data/parameter-sharing premise with a fresh declaration rather
than tune these report groups. This narrows this prototype, not all interaction
models or generic learning. The ordinary zero-headroom roots, forced-mate values,
legacy caps and all censored continuations remain available in the same index.

## Fresh coarse sharing and rule-conditioned constants

The next fixed12trajectories1000–1011 retain24roots/1037completeD2children:
7material-disagreement roots and17zero roots,314.92seconds. Three selected
training roots supply176children. The same300step/root-weighted margin fit
compares Position with Position plus3888coarse ordered-pair channels (sign of
displacement and Chebyshev distance1/2/3plus). All training regrets are0.
Position development/report regrets are2000/2000/4000/4000; coarse sharing gives
2000/2000/2000/4000. One development improvement and unchanged adverse report do
not justify expanding this ranker. Fits take.029/.091seconds.63actual root
calls take4.469/4.493/4.574seconds total for material/Position/coarse; scoring
alone takes.006/.030/.119seconds. Matched-cost Unit search gives development
2000/2000/0and report2000. No rank output becomes a numeric search leaf.

A separate exposed count-only diagnostic fits once on these same training roots,
not report labels. It worsens report regret to2285.71versus2080material and has
15.70%training pair weight at identical count inputs. Existing Unit/v2/v3 leaf
tables under identical1second/lexical search have identical choices on this
single-rule batch. This limits the current input/target, not all static prices.

A fresh four-rule declaration keeps the original generated2100–2103rules, three
whole trajectories per rule and7/16ply roots. The first two rules train; the third
is development and fourth report.24roots contain1143children;1132references
complete and11are cappedD1, leaving22complete roots,7selected and15zero.
The554.23second batch stays below its600second checkpoint. The two incomplete
report roots remain UNKNOWN; no rerun, resampling or restored holdout status.
These are exposed development rules, not unseen-rule validation.

One shared linear model uses37mechanical descriptor axes per type, summed into
signed board-current and hand-base channels, with no type/game IDs. Opportunity
curves/masks and approximate mechanism counts provide74inputs/64training-variable
columns. One300step fit on5roots/242children takes.024seconds. Training regrets
are799996400/0/0/2000/0; development2000/2000versus material2000/1750. Four
complete report roots have zero baseline headroom and no model improvement;
two report references are incomplete. All288actual root scorers and48Unit search
resource calls retain that full denominator. Do not summarize mate-scale errors
as an ordinary mean. This is an uncalibrated rank prototype, not generated prices
ready for search. Precise guard/effect operands, on-board base/promotion fields
and history are absent from its input; full rule/state/history remain in execution.

The representation has a concrete defect. Pure auxiliary/action-name relabeling
preserves its eight tested inputs; the earlier Position layout requires typed
slot permutation after castling. However, duplicating an identical guarded Pdrop
as an augment action changes raw pattern/guard/effect counts. Seventeen observed
states keep exactly the same projected physical successor sets, with34additional
action identities, yet all17inputs change. The fitted P board/hand rank changes
by-1.392/+2.650. This finite probe acknowledges distinct public action identities;
it is not a global equivalence certificate. Defer this syntactic-count input;
mere symbol invariance is insufficient for semantic consistency.
Conversely, changing the typed count guard from<3to impossible<0removes34Pdrop
options along17common reachable states, while all37old descriptor axes remain
identical. A scoped, untrained22axis proposal keeps opportunity/masks/horizon,
removes raw syntactic counts/target cardinality and appends a conservative
drop-not-statically-disabled Boolean. It matches the duplicate-rule vectors
exactly and distinguishes disabledP. Other predicates remain unknown; passing
these two controls does not establish complete rule encoding or price usefulness.

Static inputs also alias genuinely different contexts. At1100/7a quiet Cmove and
a quiet Pmove leave identical descriptor sums and hand/aux values, but finite
targets are2000and999999999. Only the latter allows Bdrop at(3,6)to checkmate.
Complete public successor scans take.532/.599seconds for79/78actions. Existing
CoreD1finds the mate in.039seconds, with two unchanged-rule repetitions; its
other-state score4000differs fromD2's2000, so this is not complete teacher recovery.
Do not build an expensive threat feature that repeats cheaper existing search.

Actual static leaves remain a separate comparison:144balanced Unit/v2/v3 calls
on all24roots useD3/20knodes/1second/q0and fixed lexical order. At1101/16v2/v3
improve finite-teacher regret2000to0; at report1110/7they worsen0to2000, with
both outcomes repeated. PVs and board/hand terms are reconstructed from saved
legal actions without rerunning search. Opposite effects and finite Unit target
bias preclude default promotion or claims of independently better prices.

An additional48existing Core ordering+TT calls keep the same Unit leaves and
D3/20knodes/1second/q0conditions. Lexical/ordered controls use54493/36591nodes,
47.027/46.629seconds, and completeD3on2/6calls. No known teacher regret changes.
Ordering and TT are changed together; sequential developmental timing, deeper
completion and fewer nodes do not establish price quality or strength. All PVs
and root states pass legality/immutability checks; no product default changes.

Decision: stop coarse-ranker expansion and defer raw syntactic rule counts.
Retain static tables and Core as operational baselines. The next input experiment
needs behavior-based shared rule fields and a concrete state interaction with
an actual cost advantage; no report refitting or new qualification framework.
Producer metadata/carrier/PV-reading failures are retained; corrections did not
repeat fits or searches. The sharing archive/index preserves models, NPZ arrays,
full denominators, failures and exact restoration instructions. Science remains OPEN.

A subsequent small audit changes Xquiet's explicit current-type target fromPtoC.
One common initial legal action now creates a different actor, yet all old type
descriptors remain identical. An untrained66axis actor relation resolves declared
promotion/explicit effect targets into the same22behavior axes, deduplicating
targets and appending their mean/max descriptors. It distinguishes changedXand
keeps the duplicate-rule vectors equal. This is a prepared approximation, not a
fit or complete rule encoder; implicit references, conditional selection, auxiliary
and history relations remain omissions. The effect-target supplement preserves
the exact rules/action/state witness and source. Next: one cost-effective shared
state interaction using typed rule relations, without refitting these report groups.

## Shared state and partial preference teachers (2026-10-09)

Two prospective whole-trajectory cohorts use the four existing full generated
rules, with two rules for training, one development and one reporting. Neither
cohort reuses earlier report labels for fitting. Cohort A has32roots/1745children,
1724complete children and21UNKNOWNs; cohort B has32roots/1700children,
1651complete and49UNKNOWNs. Each retains28complete roots. Teacher production
took836.39/765.56seconds; capped children remain unknown, never negative labels.

The shared66-axis actor descriptors are pooled into count268 or spatial938
inputs. Spatial linear terms describe individual actors and locations, not
genuine state interactions. A concrete king-location alias exposed the material
convention of a zero anchor descriptor. Exact owner/square anchor occupancy
repairs that witness in a separate1066-axis input before cohort B. Precise guard
operands, auxiliary state and relevant history remain numerical-input omissions;
full GameSession/Position semantics remain in the teacher. These are8x8 scoped
prototypes, not a replacement for the full generated-domain target.

Five fixed small fits were recovered without retraining. Cohort A's count and
spatial models both have2000regret on the selected development root. Counting
all known report roots reveals a spatial2000regression on a previously zero
root. Cohort B compares counts, anchored linear and anchored ReLU16. Across all
eight development roots, positive-regret counts are2/3/4 respectively; ReLU adds
a2000error on an unselected zero root. Across six known report roots, counts
retain two mate-scale errors, anchored linear adds one4000zero-root error, and
ReLU has zero finite-reference regret. This mixed result does not establish a
development increment or strength. Preserve all zero roots and two unknown report
roots, rather than report only the two selected report successes. Actual rank
callers total288/384 plus64matched-cost Unit controls per cohort. Rank scores
are not calibrated material prices or numeric search leaves.

A post-result count factorization agrees to about1e-14 but changes eight strict
tie choices. Integer inventory closure and stable summation diagnostics preserve
original outputs; neither numerical tolerance nor exposed-label refitting is
used to manufacture agreement. Input-range departures and absent descriptor
collisions in these four rules do not explain or prove away generalization error.

A384-call Unit resource curve on24retained roots separates search configuration
from evaluation. At2048nodes, TT+ordering has44/44known zero-regret calls versus
40/44lexical, with78.99versus84.42seconds total. At512nodes it is slower and
worse on one tie: both methods complete D2 with score0, but select children with
different D2 continuation values. At8192nodes TT+ordering retains44/44 while
lexical has42/44. Use2048TT+ordering as a scoped comparison point, not a product
default, an isolated TT attribution or a price-quality claim.

An eight-exposed-root pilot obtains partial preferences from existing Core D3
search and full-history TT identity: only depth2 entries qualify, bound direction
is reversed to the parent perspective, and mate distance is normalized. All
qualified bounds are checked against retained finite references. In24.26seconds
(20.77search+3.50probe),478children yield325certified inferior,8certified optimal
and145UNKNOWN. An incomplete root contributes only UNKNOWNs. This does not find
all cooptimal actions, prove WDL or export a stable product API. It does show a
cheaper candidate target that avoids treating every unchosen action as inferior.

Decision: retain cheap counts and existing search baselines; defer another
architecture expansion without a changed premise. Next compare fresh partial
preference coverage/cost with the decisions it could support, and distinguish
finite Unit-search compression from the project's rule-price usefulness target.
Evidence: shared-state-index.json (67verified members, five restored models) and
bound-teacher-index.json (three separately verified supplement members), under
docs/archive/search_compression_20261009. Detailed costs, failures, all roots and
UNKNOWNs are routed by data/search_compression_20261009.json. Live defaults are
unchanged; no human labels or Xiangqi holdout were read.

## Fresh partial-preference coverage and fixed same-input fits

A separately frozen cohort uses32fresh whole trajectories1600..1631 on the
same four full8x8rules, two roots per trajectory:64roots/3155children. All routes
and legal children precede teacher queries. Full childD2 lexical/noTT references
complete3133children;22caps stay UNKNOWN. There are57complete frontiers, six
incomplete frontiers and one empty terminal root, which receives no artificial
zero-regret credit. Full-history GameSession semantics remain in every search.
The complete-root D3value is audited against the normalized child frontier.

|Partial Core D3 budget|Search plus probe seconds|Completed roots|Usable optimal/inferior pair roots|Optimal / inferior / UNKNOWN|
|---|---:|---:|---:|---|
|2048nodes,5seconds|120.41|21|17|21 /447 /2687|
|8192nodes,5seconds|160.45|60|56|61 /2323 /771|

The full child references cost1371.55seconds; the whole producer finishes in
1696.86seconds. Qualified depth2 TT bounds are reversed into root perspective
and mate-distance normalized. A noncompleted root supplies only UNKNOWNs;
one-sided/cooptimal uncertainty is not a negative label. One/ six certified
labels respectively lack a complete independent child reference; retain these
unchecked denominators. The8192usable-root count is56, correcting the initial
57summary. These are finite-search preferences, not WDL certificates.

An exposed eight-root cost attribution reuses the same child depth, evaluator,
2048nodes/1second and histories with TT+ordering. Lexical child calls total184.46
seconds versus165.15ordered, but one root loses coverage:72/79versus64/79children
complete. All411children completed by both have identical scores. Configuration
helps cost modestly here and can worsen caps; it does not explain the whole
partial-label saving or prove a universal cost ratio. Original conditions and
failures stay intact; no reference or training target is replaced.

Three predeclared tiny fits differ only in full versus certified partial
supervision. All use268count axes,224train-variable columns, common normalization
from all legal training inputs, root-balanced margin1,300Adam steps and the
same seed. Full/partial2048/partial8192have28/5/28usable training roots and take
0.351/0.031/0.056seconds. UNKNOWNs never become negatives; complete full labels
accept all cooptimal actions. All three have identical development/report root
choices:3/16known development roots and4/13known report roots retain positive
finite-reference regret, including large mate-scale errors. Three report roots
remain unknown. This is no reason to expand capacity or promote a model.

All504actual root-rank calls retain the frozen choices, with two balanced
repetitions per method and every nonempty root. Median end-to-end times are
0.245/0.241/0.247/0.246seconds for Unit/full/partial2048/partial8192; successor
construction dominates, so small fit time is not deployment cost. The63cold
Unit-search controls use each root's median full-rank time, keeping caps:
positive-regret counts are3/16development and2/13report, versus3/16and4/13for
all learned ranks and5/16and6/13for Unit greedy. These counts and resource curves
are scoped diagnostics, not equivalence of error severity, calibration or strength.

A post-result exact inventory-class oracle exposes an input limit. Any truly
count-only rank with uniform class ties has irreducible regret on two development
and two report roots. For1617/16the ceiling is2000and the model also2000; for
1616/7the ceiling is1500while the model is2000. Large mate errors elsewhere have
ceiling0, so missing position information does not excuse all failures. The
oracle uses observed references only descriptively, never as a fitted predictor
or new admission gate. All model outputs remain unchanged.

Decision: retain the8192partial teacher as a cheaper scoped data option, defer
further Unit-compression fits without a decision-changing premise, and compare
the already frozen learned constants with existing independent physical-task
rewards before claiming rule-price usefulness. This exposed diagnostic must not
fit those task labels or turn them into held-out evidence. Sources, caps,
preparation failures, three models and read-only restoration are routed through
partial-preference-index.json under docs/archive/search_compression_20261009.
Teachers keep the original numeric TT ordering; a separately documented ordering
contract repair does not retroactively change these data.

That target distinction now has a read-only check on all886existing8x8common
slots, with original17background/equal-slot weights, every type and both
immediate/one-reply ordinary-removal rewards. The frozen count models factor
into signed current-plus-base constants for the unpromoted focal replacement;
hand/promotion/side offsets are kept separate. No task label is fitted. Exact
static top/pair/immediate/reply summaries match24original metrics. Full and
partial8192keep all four static highest-type choices; partial2048switches one
rule from A to B and worsens both tasks. Full changes one pair order beneficially;
partial8192improves immediate pair losses in two rules but worsens a one-reply
pair loss in one. This mixed exposed diagnostic supports neither universal
prices nor further automatic compression fits. Use a prospectively frozen new
rule sample for the next fixed-predictor task check, not these labels for tuning.

Two preselected new generator seeds2104/2105 now supply that check. Rules,16ply
routes and all five existing predictor tables were frozen before task queries;
no seed replacement, fitting or model selection. Both complete all17backgrounds:
442slots/2210type cells,5855focal transitions, with297all-zero slots retained.
Every cell is independently replayed through Core/Native legal-action sets and
full child-state identity; both rule fingerprints differ from the training rules.
The primary task takes3.57/1.47seconds; parity replay6.27seconds. It remains a
counterfactual immediate-removal task excluding anchor/history/future service,
not a whole-rule value or strength measure.

|New rule|Static top / loss|Full top / loss|Partial2048top / loss|Partial8192top / loss|
|---|---|---|---|---|
|2104|C /799/5148|C /799/5148|B /21/1870|C /799/5148|
|2105|X /977/46410|X /977/46410|X /977/46410|X /977/46410|

The previously adverse low-budget constants improve2104top loss substantially;
this does not justify selecting that model after inspecting the new outcomes.
Its B-over-C reward contrast is positive in13backgrounds, negative in one,
positive in all four early/late-owner strata, and remains positive after removing
any one background. These dependent influence ranges are not confidence intervals.
Complete pair ordering differs again: full improves2104, partial8192worsens it;
2105is mostly sparse with237/246all-zero slots. The result distinguishes price
usefulness from Unit-regret without converting one task into universal calibration.
The original follow-up was to explain2104C/B using opportunity/source/legal-
removal components without refitting labels; the crossed check below now
addresses that question. New immutable evidence is separately routed by
physical-price-transfer-index.json; previous archives stay unchanged.

The subsequent crossed population/statistic diagnosis and four prospective
initial-source-prior rules are owned by TASK_PREDICTION_DIAGNOSTIC.md. They
separate physical price-usefulness from this finite Unit-search teacher. The
new source-prior selectors improve three immediate top losses but worsen a
full pair ordering; no model refit/default promotion or further automatic
Unit-compression expansion follows. Original teachers and tables remain fixed.

## Finite-policy event prediction, 2026-10-10

This changes the supervised question, not the generic project's task domain.
At an external96ply observation point, predict owner0win/loss, a real rule draw,
or no terminal event yet. The last class gives no eventual WDL or zero utility.
Actual promotion, drops, auxiliary state, full history and repetition remain in
the executor. Technical interruption before96 is unknown, not the fourth class.
The prototype input still omits auxiliary/spatial/history interactions and any
teacher TT memory; a complete executor does not make that projection complete.
The earlier12game pilot and all its failures remain unchanged.

Four predeclared generated8x8 hybrid rules2122-2125 plus existing guardedPdrop/
X-to-P mechanics, openings0/4, three policy pairs produce24cheap games. Unit/Unit,
old frozen full/Unit and Unit/full stay separate policies. Fixed Core maximumD2,
512nodes,.25sec,q0/hard8, Unit ordering, warm per-player TT and96additionalplies
give1242plies in319.85sec. At24/48/96, terminal coverage is9/12/15of24, with
6/9/12distinct finished trajectories. The96point has8mates,7real repetitions,
9external cuts. No policy or observation threshold is selected afterward.
The same24cells at maximumD4/8192nodes/1sec cost1542.26sec,1476plies, and finish
6/10/13rows at those points:9mates,4repetitions,11cuts at96. Nine matched event
classes change. Actual resource calls stop by time1475times; only one finishesD4.
Cheap calls finishD2 on182plies andD1 on1060. These bounded algorithms with
fallbacks must not be called complete fixed-depth teachers. More time does not
monotonically create more terminal labels or establish playing improvement.

Before new labels, the first fit freezes2126-2133 with train4/dev2/report2rules,
two openings, Unit/Unit only, the original cheap caller and96cap. Preterminal
snapshots0/4/8/12 receive their remaining horizon. Every game is weighted equally
and its sampled states equally within that game. All16games complete observation:
795plies,198.17sec,58states. Existing268count axes plus remaining horizon feed
one affine4head softmax; train-variable columns alone are normalized. Zero
initialization,300Adamsteps,.01learning rate,.0001weight regularization and the
training game-balanced prior are fixed. No model selection or utility leaf.

|Game-balanced Brier/logloss|Small signed model|Training constant prior|
|---|---:|---:|
|Train|.16140/.27402|.65625/1.21301|
|Dev|.68228/3.11939|.34375/.69315|
|Report|1.54350/16.35817|.34375/.69315|

Train's win/loss/draw/no-event mix is.125/.125/.5/.25; dev/report happen to be
all genuine repetitions. Keep this restricted coverage and poor transfer.
Four affine heads fold into existing mechanical inventory ledgers plus horizon/
bias. Replay of all795actual full-history pre-move states matches every recorded
successor and numerical logits within2.14e-13, probabilities within2.62e-14.
This verifies folding, not prediction quality. On16roots,48cold rotated Unit,
encoder-discard and folded-discard calls preserve all32paired actions/PVs and
nonlatency decision/work fields. D4/2048nodes/10sec allows only oneD4completion
per arm;15node cuts remain. Each arm has32238nodes/27865scoring calls. Unit,
encoder and folded wall totals26.96/30.39/27.73sec and scoring.105/3.177/.767sec;
median paired wall ratios1.132/1.030 are descriptive local overhead. Construction
is excluded from that comparison; probabilities are discarded, never utility.

One exact signed-input group contains five different-rule initial states: one
no-event and four draws. Its all-sample unconstrained Brier floor is.025; existing
spatial moments distinguish all58inputs. Untrained unsigned current/base actor
stock totals add132axes and also distinguish those five and all58inputs. Actual
early trajectories replay after all type names change, with zero unsigned-feature
error. Equal-vector grouping is descriptive and may miss numerical near-aliases;
removing an alias does not prove learnability or resolve auxiliary/history scope.

A second prospective declaration freezes2134-2141, same4/2/2split and limits,
16games/49states/134.63sec, to compare signed269 and context401 under identical
300step fits. Context's train/dev/report Brier.00106/1.44007/1.61956 compares
with signed.17459/1.01153/.77781 and prior.56250/.93750/.68750. The new report
is half owner0wins, half real draws. All report context argmax predictions are
wrong; game-weighted.75are also confidence>.9. It separates the earlier alias
but worsens generalization. Training designs have224columns/rank16 for signed,
334/rank22 for context; held context states lie outside the training affine hull.
These coexistence measurements do not identify a causal cure. No extra fit,
calibration, model/default adoption or automatic architecture expansion follows.

Finally, clear TT before every move on all eight original Unit cells. Actions
and96event labels stay unchanged,90.76sec; this does not prove cache independence
elsewhere. A separate declaration repeats all four opening4cells twice under
cold TT, maximumD2/512nodes/10sec safety wall and unchanged96cap. All four repeat
pairs match actions, every full-state successor and nonlatency decisions/work.
The382plies take197.01sec:148D2completions,234node cuts, no wall cuts. Two of the
four event classes change versus the old.25sec policy: draw becomes win on2124,
win becomes draw on2125. This qualifies only these observed repeats. Future
price diagnostics can use this explicit bounded-node premise without calling it
optimal play, stationary full-state value or universal deterministic search.

Observed repairs are retained: the caller initially missed the test-fixture
import path; an analysis used nonexistent pv instead of principal_variation;
type-rename matching erased pattern identity and conflated a legacy move with
an effectful semantic move on the same squares. The paired declaration contained
duplicate report keys: its originally written2140/2141split was restored by
renaming the descriptive field before any fit score. Original failed source/
analysis/declaration bytes remain in recovery; no target, split or success metric
was chosen from adverse results. The corrected caller compares all available
nonlatency fields, including actual PV and semantic action identities.

Decision: retain the four-event target and cheap prior as scoped options, stop
automatic small-affine-event fits or context expansion, and use the qualified
node premise for a concrete rule-price diagnostic. A substantive same-thread
advisor followup reports all adverse fits and asks for one decision-changing
objection/next action; it is neither an approval gate nor independent execution.
Recovery: ../archive/search_compression_20261009/policy-events-20261010-index.json;
data/search_compression_20261009.json key policy_events_20261010 contains summaries.
The isolated archive has only generated sources/results and previously published
dependencies, no raw Slack/account data or operational state. Hash/metric replay
checks are distinct from reproducing hardware timings or regaining holdout status.

## Fixed-node static prices and local failure attribution,2026-10-10

The qualified node teacher now compares existing semantic-v3 against Unit with
full generated state/history execution: cold TT, maximumD2/512nodes/q0/hard8,
10second safety, fixed Unit ordering, disabled dynamic terms and root tactical
scan. Each game observes96additional plies after the same four-action opening.
No time-limit cuts occurred; incomplete iterations still fall back. This is a
declared diagnostic configuration, not a product-default change or WDL target.

Old exposed2122-2125 crosses produce449plies in235.957seconds; five of eight
event classes change, with301D1/148D2 decisions. Four prospective seeds2142-2145
are declared before outcomes; all three policy strata produce12games/587plies
in370.338seconds,312D1/275D2. Unit/Unit has three ongoing96games and one real
repetition draw. Seven of eight crossed event classes change. From v3's side,
the crosses give4wins/3losses/1ongoing, with substantial owner/rule imbalance and
dependent paths. This is useful adverse/mixed development feedback, not Elo,
universal utility, a model-selection threshold or permission to tune these labels.

Enumerating every opponent reply to every recorded selected child gives640old
children/79070replies in745.660seconds and587fresh children/79119replies in
703.135seconds. Old trajectories expose three Unit immediate-loss holes; v3
trajectories expose none. Same-parent controls show v3 retains two of those
three holes and avoids one. Fresh trajectories expose seven holes, Unit4/v3 3;
one v3 hole follows a completedD2. All saved fresh winning witnesses independently
replay. A zero witness count establishes only absence of an immediate winning
reply; dependent trajectory differences cannot establish causal price benefits.

Every fresh mating loser parent is then enumerated:936root actions and123667
enemy replies. Six roots have13/12/32/51/50/203alternatives without immediate
loss, respectively; the completedD2 v3-loss root has only one legal action and
no such alternative. Its local failure is already forced, so leaf changes at
that parent cannot cure it. At another v3 parent31actions tie for the highest
static score,27with immediate losing replies. The decisive distinction is local
exposure versus available one-reply alternatives, not eventual-WDL certification.
All seven parents and all tie sets, zeroes and actual selected actions are kept.

Existing q1 is then compared with q0 at all seven parents, both Unit/v3 leaves,
the same512total node condition and fixed ordering:28actual calls. Every q pair
keeps the same action; Unit exposes immediate loss7/7 and v3 5/7 under both.
Six roots retainD1/node-limit fallback; the locally forced root completesD2.
q1 consumes main/q work without improving this selected local decision set.
Keep this finite negative result, not a universal q limitation. The declared
root-tactical-off condition differs from the product default; a next useful
search diagnostic can compare that existing mechanism without adding leaf patches.

Thirty-two controls at all eight fresh first departures separate positive scale
and custody convention: Unit100 and Unit1000 preserve every choice/node count;
uniform1000board/900hand matches v3 at two roots, not six, and changes Unit at
four. Full-history parents and equal512node limits are retained. Several arms
finish onlyD1; timings overlap another producer and support no isolated speed
claim. Different actions alone remain attribution evidence, not gains.

Full action replay finds11old and7fresh executed Pdrop/Xtransform actions outside
v3's projected price support. All seven fresh ones are played by v3; special
opening legal sets were empty. Debug names are not semantic authority: the
global temporary flag set by Xtransform inhibits Pdrop through an equality-to0
guard. At all three actual transformed children the opponent has no P stock;
changing the flag changes no current semantic legal action. Adding one synthetic
P to that hand yields37/42/37guarded drops at flag0 versus zero at flag1. These
six fixed pairs are position-only controls, not reachable-state or utility
counterfactuals. An initial legacy-only API measurement was invalid for semantic
actions; its source/output are kept separately, and the identical pairs are
corrected through the existing semantic public iterator. No extra training follows.

The same three synthetic-stock positions crossed with eq0 versus eq1 guards
reverse those eligibility counts at both flag values. Existing sparse Position
numeric tensors agree across the variants, while rule fingerprints differ.
The encoder already binds weights to one compiled rule, so this is not its bug:
any proposed shared input must preserve the guard/effect relation as well as the
flag and stock. This falsifies raw tensor equality as a sufficient shared-rule
eligibility premise; it supplies no cross-rule utility labels or architecture win.

Adding a dormant nonpromotable X movement clone to old2122 preserves17physical
legal-successor multisets/terminal statuses and all active raw opportunity
curves, but declaration-conditioned median normalization rescales13state scores.
All837matched children/29290pair preferences and ties agree;51coldD2calls retain
physical choices/nodes. Fixed original maps restore returned scores. Compiled
IDs/fingerprints legitimately differ, so comparison uses physical successors.
This is a scoped scale inconsistency, not actor splitting, demonstrated choice
damage or general clipping/terminal-scale invariance. Measurement failures and
corrections remain recoverable; product execution was not changed.

Primary literature informs the next premise without creating a gate:
[Soemers et al.](https://arxiv.org/abs/2101.09562) compile generic state/action
tensors but report large per-game training, not a tiny shared cross-rule predictor.
[Le Lan et al.](https://proceedings.mlr.press/v151/le-lan22a.html) distinguish
representation approximation and sample-support costs; their least-squares
theorem does not bound our dependent softmax event predictions or rule shifts.
No automatic expanded input, fit or default is adopted. A2048node rerun was
rejected before execution as a result-driven frozen-budget extension and was
not run or bypassed. Existing cheap search/static baselines remain available.

Recovery: ../archive/search_compression_20261009/node-prices-20261010-index.json;
data/search_compression_20261009.json key node_prices_20261010. Restore the pinned
predecessor package first. Only generated sources, declarations, adverse outputs
and summaries are archived; raw Slack/account records and operations stay local.
Hash/denominator/witness checks do not reproduce timings or restore holdout status.

## Guard meaning, partial-root exposure and hand convention, 2026-10-10

Root-fallback delivery belongs to UNFAMILIAR_RULE_SEARCH.md; its adverse games
are price diagnostics, not a strength claim. In the introduced2147 v3/Unit
ply14 hole,141legal actions supply64 already-scored prefix children. All their
immediate replies cost8292transitions/64.320seconds. Unit100/100 and v3 with
hand=board select a move without an immediate winning reply; uniform1000/900
and unchanged v3 select losing B/Cdrops. The same enabled auxiliary truth and
zero enemy Pstock cannot distinguish this ordinary unguarded drop failure.
This exposed intervention does not select a new hand-price default.

For three previously observed Xtransform children, actual/synthetic Pstock and
flag0/1 yield12positions. Inverting a boolean guard, initial/reset value,
set_bool effect and state flag together preserves all legal sets and1124matched
one-step Position transitions. Raw sparse numeric inputs differ on all12;
compiled predicate/reset truths agree. Scope is the no-trigger global
expire_next_turn boolean family, not full history equivalence.96 scoring-discard
cold caller controls retain decisions/PV/nodes/generation/evaluation signatures;
11336predicate probes cost0.028890seconds. Local paired wall ratios near1 do
not establish utility or universal speed. Keep this scoped input primitive,
without automatically expanding a model or fitting exposed labels.

Two further rules2150/2151 are frozen before results. Opening4, five policy
strata Unit/Unit, Unit/v3, v3/Unit, Unit/v3_hand_board and v3_hand_board/Unit
share cold Core D2max512nodes/10sec safety/q0/hard8, Unit ordering and root-scan
off. Only the hand lookup changes; dynamic terms remain disabled. Ten games
produce275plies in183.151seconds,214D2/61D1, no time cuts. All275selected-child
rows are audited in173.908seconds:210distinct full-history states,65exact cache
hits,20044physical reply transitions.2150has no immediate-loss witnesses in
any trajectory; equal-hand changes two paths, including ongoing96 to a real
repetition draw.2151retains one immediate-loss child in all five policy strata.
Ongoing is not draw, and dependent paths are not independent efficacy samples.

Five distinct full-history first-divergence/loss parents supply15matched calls
and2323selected-child transitions. At2151ply3, Unit completesD2 at509nodes
and avoids the v3 loss; both v3 arms stop atD1/512 and retain it. At the other
two loss parents all arms retainD1 and the same immediate loss. Removing hand
discount therefore fails as a transferable cure. Whole275action custody
decomposition retains18drops: all have a positive v3 material delta and zero
hand=board delta. This identifies the convention's local drop bonus, not a
universal conservation law for promotion, transformation or capture.

The initial parent-control adapter accidentally let direct v3 Evaluator capture
prices affect ordering. Its source/results remain explicitly mixed-order
evidence. Corrected15calls inherit Unit capture ordering for every leaf arm;
all qualitative loss conclusions persist, with2323reply transitions. A separate
three-call observer preserves their decisions/work: Unit completes all126D2
child calls; each v3 arm completes only8 and aborts the next. Fixed capture
prices do not make alpha-beta windows or TT-guided root preferences identical.
Returned window-bound scores are not exact full-child values, so this observation
does not justify retaining a partialD2result as if its whole root were complete.

A bounded2151ply3 tie audit scores all126children, then enumerates replies only
to the union of highest-D1 ties and the UnitD2 selection: five children,
774transitions. Unit has five top ties, four immediately losing; v3 and equal-
hand each uniquely prefer the losing A move. Thus this local problem is not
only a tie among v3-best moves or a hand-discount artifact. The safe Unit action
is available, but static material weights and incompleteD2 provide different
information. Preserve both price and finite-search explanations; do not patch
the exposed position, expand its frozen search budget or fit these labels.
The first tie producer selected the wrong game's route before label execution;
the corrected run also had a mismatched raw/canonical action-format flag.
All original outputs are retained, and action-schema reconciliation qualifies
the selected-Unit flag without changing scores, ties or witness counts.

Next compare a concrete conditional service/safety input with existing search
coverage at unchanged prices and fair budgets. Neither an enlarged event model
nor a1.0hand coefficient follows automatically. Science remains OPEN.
A first cheap check uses existing semantic authority on all five2151top children:
both owner in-check flags are false for the safe move and all four losing moves.
Current check status therefore cannot supply this immediate-threat distinction.
The scoped probe retains its exact producer/provenance at
data/hand_check_probe_20261010.json; no evaluation feature is installed.
Recovery: root-scan-20261010-index.json and hand-discount-20261010-index.json
under ../archive/search_compression_20261009; both retain generated sources,
declarations, failures and adverse outputs, excluding private transport records.
