# Evaluation route decision

Direction review2026-10-09; evidence base
6f97b19fb77a62f9947aaffa9cded8dbc890e37a. This is a bounded review of existing
code/results, not a new training run, benchmark success or universal price claim.
The two scientific lines remain generic evaluation and unfamiliar-rule search.
Recent conditional tasks remain useful evidence, but further template precision
is no longer Main: either outcome alone would not select an evaluation family.

## Shared target and comparison

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
