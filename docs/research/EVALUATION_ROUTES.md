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
as a complete-domain evaluator. This is a source audit, not a reproduced failure
or measured search slowdown.

Select the small-interaction route for the next *feasibility check*, keeping
static constants as control and learned constants as a deferred comparator.
The changed premise is semantic/state interaction support, not another TDLeaf
rerun or a price coefficient fitted to exposed task tables. First audit a concrete
same-current-board/different-base-or-right state pair using existing recorded
rules: check actual continuation difference and whether the proposed features
distinguish it. A collision selects a narrow adapter repair; no collision selects
one existing-caller feature-cost measurement. Neither outcome starts training.
No need to prove full price utility or finish template exactness first.

## Evidence and adoption limits

Historical local documents: `docs/learning_phase1_tdleaf_material.md` and
`docs/learning_phase1_7_evaluation_leverage.md`. Their protocols/results remain
historical; no old phase scheduler, verdict threshold or publication gate returns.
Current conditional evidence: TASK_PREDICTION_DIAGNOSTIC.md and its archive index;
retain62/64correction, allzero support, adverse backgrounds and exposure status.

[Baxter, Tridgell and Weaver, TDLeaf(lambda)](https://arxiv.org/abs/cs/9901001)
supports combining temporal-difference learning with minimax. Its KnightCap
experiment used online FICS games; that is not an unknown-rule pure-self-play
sample-efficiency guarantee. Only the primary abstract was checked here.

Dot's complete direction reply was read and explicitly assessed. Adopt the
candidate comparison and full-domain target; do not adopt attributed statements
from another user conversation as new authority. Dot read published documents
but did not execute our measurements. Raw account/Slack evidence stays local.
Large training, extra workers and product/default changes are not authorized by
this review. Behavioral interventions can study interpretability progressively;
complete explanation is not a prerequisite for a scoped useful experiment.
