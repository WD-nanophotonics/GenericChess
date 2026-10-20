# SAME fixed-scale Generic learner: finite interface and cost feasibility

Status: feasibility only; Generic learning strength and full-domain validation
remain OPEN. No product default or other role checkout/state changed.

## Decision and exact reuse

Task2620 supports TDLeaf against initialization on one finite Chess panel but
does not select a winner over TreeStrap/WDL. The next direct-route step is a
strict SAME fixed-scale Generic comparison, rather than more Chess resolution
or an internal-target mechanism campaign. Historical task2606 used FreeModel;
it does not establish reuse of the fixed-coordinate Chess Model.

The new opt-in adapter uses the exact unchanged task2492 Model and
TDLeafEpisode classes: fixed coordinate0=1, scale10, eta.05, lambda.95. It
mechanically includes every non-anchor CURRENT board type and BASE hand type,
without a hard-coded feature width. The existing generator always declares P;
board-P is the predeclared unit, with no assumed human movement/material price.
Non-generator fixtures explicitly declare their unit type; no missing unit is
silently invented. New per-rule parameters are initialized by the same random
recipe. This is reuse of a learning procedure, not transfer of learned Chess
weights or a claim that all games have comparable absolute price units.

GameSession remains the full rule/history authority. Finite executed witnesses
cover real capture, promotion R->TP with BASE identity retained, hand/drop
capacity, auxiliary-state expiry, push/pop and full record replay. Material-only
features approximate evaluation; they do not replace rule/history execution.
RESTART/NO_CONTEST remain non-scoring UNKNOWN, never a draw reward.

## Reproduced and fixed record defect

An actual rule-legal NO_CONTEST declaration serialized successfully but failed
JSON deserialization with INVALID_OUTCOME. The parser had a stale three-value
list, while rules.schema.DECLARATION_OUTCOMES already includes NO_CONTEST.
The own sidemission parser now uses that shared authority. There is no schema
version/field change or outcome translation: actual declaration assessment still
rejects forged results at GameSession.replay.

The initial failing test receipt is retained privately.69 focused checks pass
across the new adapter contract, Session record/serialization, initial layouts
and declaration semantics. All four supported declaration outcomes roundtrip;
unknown strings and a forged NO_CONTEST on a WIN rule remain rejected. This
is an additive isolated record fix, not a PRIMARY rollout or engine/UI default.
It occurred after task2620's original evaluator closed and does not change its
Chess rule authority or registered source bytes.

## Preserved opening negative and active-feature probe

The initial four-development-rule opening smoke performed16 complete queries
and439 nodes. All four parameter updates were zero. It establishes interface
execution, not learning, and remains unchanged.

A new bounded registration changed only outcome-blind history preparation:
first two eligible nonterminal8-ply histories per rule, with a nonzero non-fixed
inventory channel, selected before search/loss/reward inspection. All8 roots
were found;29 queries used1888 nodes. Six cases produced a nonzero parameter
update. Seven endings remain horizon UNKNOWN and one is an actual rule win.
These are development excitation witnesses, not independent strength samples;
no root, price, seed or hyperparameter was selected from the update result.

## Cost checkpoint and independent record/update audit

The separately registered cost-only batch cycled those two exposed roots per
development rule, one fixed initialization each,80k combined candidate-plus-foe
nodes per arm. All four arms reached their original caps:320000 nodes in
99.868s,5707 queries and258 episodes (254 actual terminal,4 UNKNOWN).
The candidate/foe split is preserved, including three incomplete final searches
and one cap-ended nonterminal episode. The fixed coefficient and scale stayed
unchanged;210 episode updates were nonzero. One signed hand coefficient is
negative; it is retained without clipping, tuning or selecting a preferred arm.

Every action/full-history record, actual outcome, both-side node total and TD
update reconstructed from the logged receipts passed independent audit. This
does not independently recompute every search target. The workload is repeated
development input, not a holdout, method comparison, or evidence of strength.

The slowest observed arm cost was28.141s/80k nodes. Scaling that to a prospective
4M-node training batch gives1407.045s; a50percent runtime margin gives2110.568s.
A previous complete Generic evaluation cost source is task2609:1536 slots in
691.419s, H128, D2, same four rules but different models/search ordering. A
1024-slot projection with the same50percent margin is691.419s. Adding1200s for
preparation/audit gives4001.988s (66.700min). This is a source-bound feasibility
estimate only, not a launch registration or completion guarantee. Both cost
sources and their hashes are in cost-feasibility.json.

## Next action and limits

Implement and preregister a controlled SAME fixed-scale TDLeaf-versus-initial
comparison on these four development rules: four initializations,250k paid
nodes per rule/seed arm (4M total), and a complete shared1024-slot H128/D2
evaluation. Before launch, freeze all sources, seed recipe, full-history training
pool and exact-disjoint evaluation starts, fixed foe, both roles, budgets and
whole-run origin; refresh the estimate including actual preparation. Retain
every negative cell, UNKNOWN and missing slot. A scope/cost change reaching
120minutes first needs the existing Chat mailbox assessment; do not split it
or extend old caps. No new strength batch is registered or launched here.

Four old rules, one cost-scan initialization and finite semantic witnesses do
not establish unfamiliar-rule generalization, descendant/transposition
independence, complete generated-domain coverage, stable price ratios or
population effects. Broader rules remain the long-term target. This checkpoint
advances its fixed-scale interface and practical cost question without claiming
that a scoped prototype completes that target.
