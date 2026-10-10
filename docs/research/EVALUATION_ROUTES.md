# Evaluation route decision

Direction review2026-10-09; evidence base
6f97b19fb77a62f9947aaffa9cded8dbc890e37a. This is a bounded review of existing
code/results, not a new training run, benchmark success or universal price claim.
The two scientific lines remain generic evaluation and unfamiliar-rule search.
Recent conditional tasks remain useful evidence, but further template precision
is no longer Main: either outcome alone would not select an evaluation family.

## Shared target and comparison

Latest allocation checkpoint2026-10-10: retain installed Core/static baselines.
The fresh2180-2183 fixed small completion prepass+residual Core cohort finishes
16games645plies, but its eight resolved roots contain no nonterminal winning
resolution. Four saved identical-history Core matches already have the same
mate-range sign; unmatched roots do not establish a gap. Separate freshD6/q0
16games753plies also resolve only5immediate wins/3ongoing losses, with6same-sign
saved Core matches; all actual Core calls hit time limits, completingD1-D4.
No automatic cap, feature or model expansion follows. Predeclared common-parent/
selected-child diagnostics qualify the final choice. On47predeclaredD2common
parents all chosen actions/exposures agree, with one residualD2-to-D1 retreat
and caller50.330sec Core/52.461sec combined. This fixed local sample supports
deferring the allocation, not forbidding all completion-aware methods.
The56D6common-parent choices/exposures also agree. Its caller saving belongs
to two already-known resolved shortcuts;54unknown deferrals cost109.542sec
Core/110.003sec combined. Next examine response-support placement/reuse, not
an unconditional per-leaf scan or a larger prepass. No model/default changes.
COMPLETION_SEARCH_FEASIBILITY.md owns the costs and recovery.
Conditional response support remains a candidate premise: identical checking-
drop counts/stock/right eligibility still alias a unique legal capture response
with actual checkmate. This is not a five-label fit or hand-value correction.

Earlier decision2026-10-10: retain static-v3 and Unit as cheap scoped baselines;
do not adopt hand=board from one exposed drop hole. Two new rules/10games plus
same-parent fixed-order checks retain adverse price and incomplete-search
effects. Compiled guard/reset truth is a cheap supported input premise, not a
learned utility. Next select one conditional service/safety versus finite-root
coverage question, rather than automatically expand event fits or custody-law
constants. FINITE_SEARCH_COMPRESSION.md owns the qualified whole-cohort evidence;
UNFAMILIAR_RULE_SEARCH.md owns the separate completed-root-fallback correction.

One relevant alternative is rule-conditioned selection among cheap evaluators.
[Stephenson et al.](https://arxiv.org/html/2105.12846) estimate heuristic win-rates
on695 Ludii games using depth2 search and at least100 games per heuristic,
then regress those rates from ludeme-presence descriptions with leave-one-game-
out checks. Their descriptors omit string, numeric and boolean values. This is
heuristic selection, not generation of universal piece prices or a shared state
value function. The reported label-generation scale also differs sharply from
our two-rule pilot. Inference for this project: such a selector is a retained
alternative, but token presence alone may omit the guard/effect direction our
actual eligibility controls require. No new selector, training batch or proof
gate is introduced; first retain typed behavioral meaning and a discriminating
same-budget diagnostic.

Generic means the complete project-generated rule domain, with rule semantics,
board shape, current/base actor identity, promotion, hands/drops, auxiliary rights
and history affecting legality or returns. Search/adjudication must retain this
state even when a scoped cheap evaluator intentionally ignores a component.
A state-blind baseline is allowed; it is not a sufficient learned state encoding.
Mechanically compiling features per RuleSet is compatible with generic design;
hand-written chess/shogi solutions do not establish it. Rule-specific learned
weights also do not demonstrate transfer to a new RuleSet without retraining.

|Route|Inputs and signal|Retained evidence and changed premise needed|Cost / smallest unknown|
|---|---|---|---|
|Rule-generated constants|Compiled supported rule geometry/context assumptions; no learned labels; material counts at leaf, full semantic search outside it|Retain as inexpensive baseline. v2/v3 rank identically in the recent cohort; top-choice and full ordering results differ. Template-any signal is exposed/conditional, not universal utility.|Profile construction is amortizable; direct leaf material scan scales with board plus hand entries. Unknown: whether a concrete conditional failure actually warrants changing the candidate rather than only its interpretation.|
|Learned then frozen constants|Existing RuleSet-fingerprinted board-current/hand-base weights; TDLeaf samples from fixed-search self-play|Historical early PROMISING arena is explicitly unaudited; later evaluation-sensitive and mixed tests report NO_POSITIVE_SIGNAL. Learned directions had much less decision leverage than artificial perturbations. Repeating the same pipeline has no new premise.|Training includes searched trajectories and PV replay; inference can reuse material tables, but exact current runtime cost is unmeasured. Unknown: a changed signal/representation that predicts useful directions, without fitting exposed or human labels.|
|Small state-interaction evaluator|Retain current material baseline and mechanically derived semantic/state interactions; a potential learned residual needs a declared return/teacher signal and full state contract|Existing semantic attack/defense extractor and compact residual are reusable prototypes, not complete-domain certification. Counterfactual equal-material task differences motivate interaction capacity but do not prove learning gains.|A dense width-H residual costs roughly O(DH) arithmetic per full forward pass, derived from its matrix shapes; attack features additionally invoke semantic queries. Incremental savings require correct event invalidation, not assumed NNUE speed. Unknown: can the current adapter distinguish a relevant state pair and run within the existing caller budget?|

Cost expressions above are engineering estimates, not measured training budgets
or claims that a particular model is faster. Compare total feature/search/recording
cost, not network arithmetic alone; use matched conditions or resource curves.

## Existing code changes the next choice

Locally inspected `generic_chess/learning/features.py::material_features` counts
current board types and base hand types. It has no spatial/history representation;
that limits the model, not the semantic search state.
`tactical_interaction_features` uses the actual compiled semantic attack engine,
and refuses unsupported legacy substitution. Reuse that authority if needed.

`generic_chess/learning/nonlinear.py::semantic_state_features` currently accepts
Position, compiled rules and supplied dynamic values. It encodes current-type
occupancy, hand counts, side and auxiliary slots. It calls `board_size()`, which
raises for rectangular carriers, and receives no GameState history. Board-piece
base identity is not explicitly encoded; supplied dynamic values might resolve
some distinctions, so collision claims need an actual controlled pair. The
existing residual is therefore retained as a scoped prototype, not plugged in
as a complete-domain evaluator. The subsequent actual custody/history controls,
rectangular sparse prototype and caller measurements are recorded in
STATE_INPUT_FEASIBILITY.md; the original source audit alone was not a failure
or slowdown measurement.

Select the small-interaction route for the next *feasibility check*, keeping
static constants as control and learned constants as a deferred comparator.
The changed premise is semantic/state interaction support, not another TDLeaf
rerun or a price coefficient fitted to exposed task tables. First audit a concrete
same-current-board/different-base-or-right state pair using existing recorded
rules: check actual continuation difference and whether the proposed features
distinguish it. A collision selects a narrow adapter repair; no collision selects
one existing-caller feature-cost measurement. Neither outcome starts training.
No need to prove full price utility or finish template exactness first.

The first feasibility study is now complete: a consequential base-identity
collision is reproduced with fixed dynamic inputs; a separate offline sparse
Position layout preserves current/base/promoted/hand/aux fields across tested
shapes, while explicitly omitting history. All135prospectively frozen children
of one exposed generated rule completeD2. Within1710same-material pairs there
are229finite teacher differences and1481ties; siblings are dependent. Full
Position and semantic relations separate those differences; coarse3x3 aliases4.
This does not establish learning gains or a need for nonlinearity. Eighty actual
caller controls show repeated semantic relations cost far more than their36
dimensions suggest, while sparse recomputation is modest locally and can still
lose a near-boundary completed depth. Retain sparse Position/material/coarse
controls; defer per-leaf attack extraction and any automatic training. The next
question is a declared compact-predictor decision/target/split, not another
encoding theorem or a strength claim. Exact caps/failures/denominators:
STATE_INPUT_FEASIBILITY.md and data/state_inputs_20261009.json.

A same-batch no-fit sum constraint also excludes exact affine reproduction of
four independently checked teacher values, while not proving ranking failure
or neural-network necessity. A mechanically generated relative-pair histogram
breaks this constraint at modest local caller cost, so retain it as an optional
interaction comparator. Its semantic exclusions and42/48D2completion count
remain explicit. No exact-fit requirement or automatic training follows.

The next target/split decision is now concrete: retain finite unit-D2 search
compression on six new whole trajectories, with all228children and three
zero-regret unit-greedy roots. Stop the uninformative D4 arm after55caps; do
not require deeper certification. A single width16,72training-child protocol
and default-no-training runner were prepared before authorization. User2026-10-09
now permits appropriate small local training; runs expected to exceed one hour
first require dot's necessity assessment (LOCAL_AGENT.md Budget).
Matching this teacher measures compression,
not true utility or the benefit of learned-leaf search. Existing TT/ordering and
rule-generated table controls retain adverse finite-budget/tie/cap outcomes.
Current actionable evidence and exact recovery: FINITE_SEARCH_COMPRESSION.md.

The later physical-target comparison motivates a changed static *source prior*,
not more Unit-teacher fitting: on four prospectively frozen new rules, equal
initial ordinary-source capture-count/total selectors improve immediate top loss
in three and tie one, but full ordering worsens in one. One-reply support stays
sparse and context-dependent. TASK_PREDICTION_DIAGNOSTIC.md owns the crossed
population/statistic attribution, costs, exclusions and adverse evidence. Keep
this as a scoped comparator; actual leaf-interface sensitivity is separate from
price usefulness. No universal source law, replacement default or strength claim.

The first executed matched input comparison is now conditional root ranking,
not a new numerical leaf model. Twelve fresh whole trajectories yield24complete
frontiers/1055references;7teacher/material-disagreement roots are selected before
candidate prediction, while17zero roots remain in the denominator. Position and
Position+relative-pair models share202trainchildren, fixed root-weighted margin
loss and fit budget. They have identical development/report regrets2000/4000/0;
relative pairs cost more without a choice benefit. Matched-budget Unit search
has0regret on those three roots. Keep Core baseline and defer pair expansion or
rank-score leaf binding. The one mate-scale improvement over greedy and the two
adverse roots are separate results, not a deployment success. Fresh data and a
specific sharing/support premise are needed before another candidate fit;
no retuning or resampling of these report groups. Full conditions/recovery remain
in FINITE_SEARCH_COMPRESSION.md and its existing data index.

## Evidence and adoption limits

Next sharing premise: train-only pooling reduces ordered-pair channels from
32400to3888 and variable columns from5566to1592, retaining the full Position
input. Four independent actor-loop checks preserve pair totals. This is a
support/size observation, not an accuracy or live-cost result; pooled geometry
aliases remain explicit. Compare it only on newly declared whole trajectories,
with the existing Position and search controls, rather than refit these reports.

Primary-literature scope check: [Ludii/Polygames](https://arxiv.org/abs/2101.09562)
automatically constructs state/action tensors across games, but its stated
encoding covers common rather than all state variables and omits some move
properties. [Fully convolutional transfer](https://arxiv.org/abs/2102.12375)
studies mapped state/action representations and reports both positive and
negative transfer. Our inference: spatial sharing or variable board size alone
does not establish full generated-rule semantics or useful unseen-rule transfer.
Keep mechanical semantic mapping and explicit history/auxiliary exclusions;
these papers motivate a scoped fresh comparison, not a new framework or large
training run. Any proposed single run above one hour still needs dot's necessity
assessment under the user's current policy.

Historical local documents: `docs/learning_phase1_tdleaf_material.md` and
`docs/learning_phase1_7_evaluation_leverage.md`. Their protocols/results remain
historical; no old phase scheduler, verdict threshold or publication gate returns.
Current conditional evidence: TASK_PREDICTION_DIAGNOSTIC.md and its archive index;
retain62/64correction, allzero support, adverse backgrounds and exposure status.

[Baxter, Tridgell and Weaver, TDLeaf(lambda)](https://arxiv.org/abs/cs/9901001)
supports combining temporal-difference learning with minimax. Sections4–5
were subsequently checked: updates use minimax PV leaves and temporal
differences of searched states; the experiments distinguish initialization
and opponent/data conditions. A fixed finite-teacher regression pilot is
different from that procedure. The FICS experiment is not an unknown-rule
pure-self-play sample-efficiency guarantee.

Dot's complete direction reply was read and explicitly assessed. Adopt the
candidate comparison and full-domain target; do not adopt attributed statements
from another user conversation as new authority. Dot read published documents
but did not execute our measurements. Raw account/Slack evidence stays local.
Large training, extra workers and product/default changes are not authorized by
this review. Behavioral interventions can study interpretability progressively;
complete explanation is not a prerequisite for a scoped useful experiment.

The fresh sharing comparison narrows the immediate choice. Coarse spatial ranks
improve one development root but leave adverse report regret unchanged; matched
Unit search remains competitive. Four-rule constant-input training has no clear
held-rule choice benefit, two report references stay incomplete, and raw IR
declaration counts fail a concrete redundant-drop representation control. Predicate
operands also matter: disabling Pdrop leaves the old descriptor unchanged.
Retain an untrained22axis behavior-based proposal as a scoped repair, not a new
price table. Any small state interaction must beat a useful existing alternative
per cost: CoreD1detects the observed drop mate in39ms, whereas complete successor
feature scans cost over500ms. Static v2/v3leaves have both a helpful and an adverse
searched choice at identical conditions. Do not conflate root-rank failure with
static-leaf failure, or finite Unit agreement with true utility. Exact evidence:
FINITE_SEARCH_COMPRESSION.md and the shared-rule archive/index. No default changes.

## Latest decision: shared state versus cheaper finite preferences

The2026-10-09 shared-state comparison retains64fresh roots across two independent
trajectory cohorts, with70capped child references left UNKNOWN. Anchored ReLU16
fits its training choices and removes two selected report errors, but increases
development errors including a zero-root regression. Anchored linear also adds
a report zero-root error. This is no clear development increment justifying
architecture expansion or default promotion. The numerical inputs still omit
precise guard operands/auxiliary/history; full-state teachers are not restricted.
The concrete zero-anchor input alias is repaired separately, not excused by
missing position modeling. No report refits or price/strength claims follow.

Keep count and Core search baselines. A partial-bound teacher pilot supplies
325inferior/8optimal/145unknown child preferences in24.26seconds on eight exposed
roots without labeling all unchosen actions negative. The next cost-sensitive
choice is whether fresh preference coverage supports useful shared decisions,
or whether the target should move away from compression of Unit search toward
rule-price diagnostics. One new decision question precedes another fit; this
does not ban learning, demand exact WDL or require advisor approval for short
independent work. Full evidence: FINITE_SEARCH_COMPRESSION.md and its data index.

The next prospective64root/3155child comparison qualifies a cheaper supervision
option rather than a larger evaluator. At8192nodes partial bounds supply56usable
pair roots in160.45seconds, versus1371.55seconds for full child references;
2048nodes leave only five usable training roots. Three fixed common-input fits
have identical development/report choices with substantial errors. Actual
root-rank callers cost about0.24seconds per root; matched-time existing search
has fewer positive report errors, with caps/severity retained separately.
Counts have some irreducible inventory-class losses but also avoidable errors.
Do not expand architectures, refit reports or mistake finite Unit compression
for useful generic prices. Next use the frozen models only as exposed predictors
on an existing independent task reward, alongside static and blind baselines;
this tests the target distinction without new fitting or a new task framework.

The read-only check on all886existing8x8slots now gives no top-choice gain for
full or partial8192constants; partial2048worsens one rule. Complete pair ordering
has mixed immediate/reply differences. Retain those exposed results. The next
test needs fixed predictions on predeclared new rules and the same physical
reward/weights, without refitting old labels or expanding models.

That two-rule prospective check is complete:442slots/2210cells, all zeros and
Core/Native parity retained. Static/full/partial8192chooseC on2104; the frozen
partial2048choosesB and has lower immediate-task loss21/1870versus799/5148.
All chooseX on the mostly zero2105. Complete pair ordering has mixed differences.
Do not select a model or fit these new report outcomes. The subsequent crossed
source/occupancy/statistic checks and four new-rule source-prior candidates are
now recorded in TASK_PREDICTION_DIAGNOSTIC.md. Counterfactual top-choice gains
transfer weakly to actual fixed-search selected actions: capture has limited
improvements and one adverse q0 result; total ties throughout. Keep these scoped
candidates, not automatic Unit-regret training or a default joint price system.

Latest2026-10-09 checkpoint: four further finite16source rules give no selected
net improvement, with five q0 and one q2 regressions. On twelve exposed roots,
all36matched D2 calls complete; five finite16 losses remain. An independently
fixed Unit-D2 full child reference and an existing frozen partial2048 constant
comparator require no label fitting: v3 hits12/12, initialcapture6/12,
finite16capture7/12 and the frozen learned constants6/12. This narrow teacher
diagnostic does not establish generic price utility or rank evaluator families.
It also does not show every constant system fails or require state interactions.
Current choice is to stop automatic source-law/horizon expansion and exposed
refits; select a concrete future target by decision and cost. Preserve real
promotion/drop/auxiliary/history semantics, while stating that full state is
not full value. Detailed controls and raw recovery remain in
TASK_PREDICTION_DIAGNOSTIC.md. Advisor advice to refit these exposed roots is
deferred under the no-exposed-label-fitting boundary; small authorized training
on a separately declared prospective development split remains available.

Latest frozen-transfer decision: the current-board proxy is not the original
predictor. Original hand terms restore its choices on34 roots; conditional
no-fit role projection has a small finite paired gain but none on34 further
roots. Keep both as scoped comparators, no refit/default. Current terminal/mask
handling resolves the observed expiring-right case; persistent rights expose
latent continuation differences with identical count inputs. Next investigate
that concrete support boundary, rather than enlarging a network automatically.
Scoring-discard algebraic folding reduces forward overhead without changing
search utility. TASK_PREDICTION_DIAGNOSTIC.md and UNFAMILIAR_RULE_SEARCH.md own
raw denominators, scope, costs and isolated recovery. The two research lines
and small-training authorization remain unchanged.

## Latent capability and actual leaf binding, 2026-10-10

The predeclared2118/2119 continuation does not reproduce the earlier61
common-action target conflicts: eight eligible opponent-P-stock roots in2118,
none in2119,32complete gate/lifetime fronts and no changed common-action
UnitD2labels. Empty eligibility is retained. Availability still changes some
optimal sets. This limits transfer of the old fixture; it does not establish
that auxiliary rights are irrelevant or that count inputs suffice generally.

An untrained264axis probe resolves actual bool-drop guard operands and lifetime
against mechanical actor descriptors and hand stock. It separates the61old
aliases and preserves eight renamed-slot/inert-slot/type controls, including
public legal children and terminal checks. A supported disjoint-drop-zone pair
still aliases: equal pooled actors/permission, different four-square drop sets.
Keep this as a limited probe; do not enlarge/train it as a complete-domain
repair. Full execution continues to preserve spatial/auxiliary/history semantics.

Primary sources inform the representation choice, not its utility. The existing
[Ludii study](https://arxiv.org/html/2101.09562) trains a separate model per game;
its tensor/action approximations and resource setup are not a local shared-model
efficiency guarantee. [Gunawan et al.](https://proceedings.kr.org/2022/46/kr2022-0046-gunawan-et-al.pdf)
use rule-linked graphs with anonymous label relations; sections5.1-5.2 evaluate
legal-action and next-fluent inference, including mixed and sometimes successful
zero-step transfer. These are not learned utility or playing-strength results.
Our inference: preserve the connection between a precondition and the capability
it enables, while evaluating a scoped adapter before choosing a larger model.
[Stockfish's NNUE documentation](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html)
distinguishes accumulator refresh from feature-delta updates. A generic compound
action needs correct dependency invalidation; chess update cost is not our bound.

The full frozen rank predictor has been examined as an actual leaf, keeping
its complete affine terms, fixed Unit ordering, original histories and explicit
mechanical scale. Pairwise ranking does not identify a utility offset or calibrated
draw value: adding an intercept leaves every within-root margin unchanged.
Fixed scaling/role controls are diagnostic, without exposed-label fitting or
selection. Separate finite teacher errors, immediate legal mating replies,
completion and cost; an enlarged state model cannot be inferred from changed
searched choices. Exact outcomes are owned by TASK_PREDICTION_DIAGNOSTIC.md and
UNFAMILIAR_RULE_SEARCH.md rather than another framework or admission gate.

The completed510matched caller controls do not select a new scale/model/qdefault.
Selected D3targets retain one adverse gap and turn another into a tie. A new
12game terminal-signal pilot gives3one-ply mates from one opening,4actual
repetition draws and5censored trajectories; censoring changes with policy.
This is insufficiently varied return information for the next fit. Keep unknown
outcomes explicit and declare signal/sampling before spending on training.

[Pardo et al., Time Limits in Reinforcement Learning](https://proceedings.mlr.press/v80/pardo18a.html)
distinguish task termination from external interaction cuts. Their partial-episode
bootstrap requires reliable value predictions and sufficient exploration. Our
inference: an external24ply cap does not create a draw, and our uncalibrated rank
predictor does not supply a justified bootstrap. Rule-defined repetition remains
a genuine terminal. This source motivates label semantics, not a chess utility
guarantee or automatic training implementation.

Post-publication trajectory audit: the seven completed game rows contain only
three distinct seed/opening/action trajectories, with multiplicities3/2/2.
Thus repeated policy arms are not seven independent return examples. The next
cheap question is whether a prospectively declared broader rule/opening sample
supplies varied actual returns at fixed cost. Keep all censored rows and policy
strata in the denominator; a new pilot must not retroactively extend these12
games or turn their unknowns into draws. An initial four-rule sample with common
bounded callers and declared24/48/96ply observation checkpoints can measure
return availability versus cost, without choosing the best threshold afterward.
Only use that evidence to decide between terminal supervision and a separately
declared alternative signal; no fixed sample-size gate or automatic training.

## Prospective finite-policy events, 2026-10-10

Four new predeclared2122-2125 rules, two openings and three Unit/full policy
pairs supply24games at common Core D2/512nodes/.25sec/q0. All full state and
actual rule-defined terminals remain. Declared24/48/96ply observations have
9/12/15finished rows and6/9/12distinct finished trajectories;96plies contains
8mates,7repetition draws,9external cuts.1242played plies cost319.85sec. No old
game is extended or resampled. These are diagnostic trajectories, not Elo/WDL.
A separately declared same24cell D4/8192nodes/1sec curve costs1542.26sec for
1476plies. Its24/48/96points have6/10/13finished rows and4/8/11distinct finished
trajectories;96plies has9mates,4repetitions,11external cuts. Nine matched cells
change event class. One cheap14ply mate becomes ongoing at96. More resource
does not monotonically increase terminal coverage or establish stronger play.
The first action differs in21/24cells. Actual completed depths matter: cheap
calls complete D2 on182/1242plies and D1 on1060; resource calls finish D1/D2/D3/
D4 on772/560/143/1plies, with1475time limits. These are bounded algorithms with
fallbacks, not full fixed-depth policies or budget-independent values. Local
timing and overlapping cost categories do not isolate depth/time/cache effects.

A new small training declaration fixes eight further rule seeds2126-2133,
train4/dev2/report2, all Unit/Unit teacher games, openings0/4 and96ply external
caps before outcomes. Four labels explicitly mean owner0 win/loss, real draw,
or no terminal event before the cap. The fourth is a known finite-event label
while eventual WDL remains unknown. Sample preterminal states0/4/8/12, equal
weight per game and within its snapshots; include remaining external horizon.
Use existing268count axes and a single small affine softmax fit versus training
class priors, fixed300steps/.01/.0001; report Brier/logloss and per-rule coverage.
No model selection or live leaf. This measures a scoped finite-policy prediction
option, not rule-only price usefulness. Count inputs omit auxiliary/spatial/history
interactions and teacher warm-TT memory despite full executor semantics. The
teacher is a bounded algorithm, not an exact stationary policy. Preserve failures
and zero/unseen classes; no exposed fitting, bootstrap or censorship-to-draw.

Advisor review agrees with the four-event target and remaining horizon, and
objects to completed-only return regression despite rule-level splitting.
Adopt that distinction and policy stratification; a technical interruption before
the observation point cannot count as no-event-at96. The new fit admits only
completed generation records, including genuinely observed ongoing96games.
Defer numeric leaf use. The resource diagnostic already has a distinct question:
how labels depend on the bounded teacher budget, not how to accumulate more
finished games or pass a training gate. No model/default or extra worker follows
from this consultation. Its published-document review did not execute local data.

The declared16games finish in198.17sec with795plies and58sampled states.
The fixed model's train/dev/report Brier is.16140/.68228/1.54350 versus prior
.65625/.34375/.34375; corresponding report logloss is16.35817 versus.69315.
Dev/report happen to contain only true repetition draws. Keep that narrow
coverage and the overconfident failure; no calibration, refit or leaf adoption.
Five different-rule initial states have identical signed counts/remaining input
but ongoing-versus-draw labels. Existing spatial moments separate this observed
alias; untrained132unsigned current/base actor totals also separate it and all58
sampled inputs. Type-renamed actual early trajectories give zero context error.
Neither exact separation nor a zero empirical oracle floor proves learnability.

A second declaration fixes2134-2141 before outcomes, same4/2/2rule split,
16Unit games,49states,134.63sec. Two affine arms share300steps and game weights:

|Brier, lower is better|Signed269|Context401|Constant prior|
|---|---:|---:|---:|
|Train|.17459|.00106|.56250|
|Dev|1.01153|1.44007|.93750|
|Report|.77781|1.61956|.68750|

The new report contains wins and draws; extra context still worsens transfer.
Context401's report argmax is wrong at all game-balanced sampled states, with
.75weighted wrong-and-confidence-over.9. Its training design has334columns but
rank22, versus224/rank16 for signed269. Held inputs and confident errors coexist;
these descriptive support measures do not identify a sufficient causal repair.
Stop automatic context expansion or same small-affine-event fits. Keep the
finite-event target as a scoped option and the prior as the cheaper comparator;
the next useful premise must address teacher reproducibility or cross-rule
support, rather than treat more features as an established cure.
Exact folding agrees on795full-history states within2.14e-13logit error.
Forty-eight scoring-discard calls preserve all32paired decisions/PVs/work;
encoder/folded median wall ratios1.132/1.030 are local overhead, not useful leaves.
FINITE_SEARCH_COMPRESSION.md owns detailed outputs, caps, failures and recovery.

The subsequent fixed512node price diagnostic keeps full generated mechanics and
compares Unit with the existing static v3, without a new fit or product default.
Fresh four-rule crosses give v3-side4wins/3losses/1ongoing, with owner imbalance
and dependent paths. At all eight first departures, multiplying Unit prices by10
preserves choices/work; a uniform hand discount alone matches v3 at only two.
Executed guarded drops/transforms remain outside v3's projected price support.
The global temporary flag inhibits Pdrop; at three actual transform children
there is no P stock, so changing the flag changes no current semantic action.
Adding one synthetic P makes37/42/37drops eligible at flag0 and none at flag1.
This is a scoped, position-only interaction control, not reachable-state utility
or proof that the flag caused any game outcome. Preserve rule-conditioned effects
and inventory prerequisites before another shared-input experiment. Existing
search, Unit and static tables remain cheap comparators; local mate/front/q
diagnostics do not authorize a refit or establish long-term survival.
FINITE_SEARCH_COMPRESSION.md and node_prices_20261010 own the exact evidence.

The semantic relation follow-up separates input identifiability from usefulness:
current hanging counts distinguish five exposed top children but miss silent
ordinary mating drops in the complete cohort. No fit or feature penalty follows.
An alternative completion-aware search prototype retains resolved outcomes apart
from heuristics and preserves full state/history; its512successors are not the
old512alpha-beta nodes. Initial one-second fresh-rule crosses do not establish
an affordable advantage. COMPLETION_SEARCH_FEASIBILITY.md owns algorithm/source
limits, actual costs and the fixed scheduling-sensitivity repeat. Continue with
one decision-changing attribution/cost question; keep static and installed search
as cheap comparators, not a mandatory gate before every evaluation candidate.

The controlled completion follow-up does not support the unmodified expensive
frontier default: ON/OFF win counts reverse with budget and a fresh coldD2
route wins5 versus3 with about half the summed caller cost on unlike paths.
Three finite winning resolutions remain beyond the completedD2 baseline;
two resolve in a small fixed-work frontier. Retain one prospective combined-
total-budget hypothesis, not an exposed fitted policy or proof gate. Checking-
drop incidence aliases one safe/two unsafe children and is insufficient alone.
COMPLETION_SEARCH_FEASIBILITY.md and completion_ablation_20261010 own the full
scope, counts, caps, timing correction and isolated recovery.
