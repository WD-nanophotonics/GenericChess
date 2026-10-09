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
