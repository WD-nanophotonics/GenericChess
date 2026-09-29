# Research direction options after scalar-prior design gate

The model-design synthesis closed with `NO_DEFENSIBLE_COMPLETE_SCALAR_HYPOTHESIS`.
RuleSet semantics and terminal W/D/L outcomes do not choose a cardinal map from
heterogeneous, context-dependent capabilities to one type-local material unit.
The current mainline therefore asks which additional game-independent modeling
assumption, if any, is acceptable. This note consolidates the three existing
options and their costs; it does not select one or propose a formula.

| Direction | Additional assumption | Smallest falsifier | Compute cost | Holdout impact |
| --- | --- | --- | --- | --- |
| Rule-derived context ensemble | A declared set or measure over legal contexts represents the contexts relevant to evaluation. Rules define legality and reachability, not typical-state frequency. | A tiny RuleSet with two legal contexts that reverse the local ordering of the same type pair. Predeclare the included contexts and weights; check whether a plausible change in context mass reverses the aggregate conclusion. | Low for a few fixed contexts; potentially large for broad enumeration over board, hand, and history states. | Rule-only work consumes no material-value holdout. If Chess or Shogi reference values influence selection, those games become diagnostic. Reading Xiangqi rules alone does not consume its material-value holdout; using Xiangqi value evidence to shape the formula would. |
| Bounded gameplay calibration | Results depend on a declared strategy family, strength range, starting-state distribution, opponent model, horizon, and outcome objective. Game performance does not by itself identify a context-independent material unit. | A tiny finite game where an exchange matters against one response policy but is irrelevant under exact W/D/L play. If the calibration conclusion changes with policy or seed, that dependency must be part of the model. | Highest: even a small game needs repeated trials across policies and starts to separate policy effects from game outcomes. Arena/self-play/Heavy remain unauthorized by the current mainline. | Calibrating on a ruleset consumes its independent gameplay-holdout role. It need not use human material values, but Xiangqi self-play would make its gameplay a diagnostic even if its material values stayed unseen. |
| Structural or ordinal results only | Report context-indexed simulation/dominance relations and accept incomparability and context reversals; do not aggregate them into a scalar or type-level total order. | A two-context transition graph where the relation reverses between contexts. This matches the already observed context-dependent simulation result. | Lowest for bounded local witnesses; full state-space coverage can still be large. No games or training are needed. | No human material values are required, so material-value holdouts remain untouched. Rule semantics may be inspected without consuming the Xiangqi material-value holdout. |

## Evidence and limits

The existing rule-only scalar family and AMTU candidate were negative within
their declared tests. The neutral-kernel and simulation-to-scalar routes did
not justify a context aggregation. Immediate recapture and capture-to-hand
re-entry are real rule consequences, but their effect on type-to-type value
still depends on context, strategy, or frequency assumptions. The real-Shogi
drop-seed filter was a no-op. Pell's METAGAMER supplies rule-derived advisor
precedent, not a universal exchange-weight axiom.

These historical boundaries are recorded in
`docs/archive/courier_worker_20260928/CURRENT_MAINLINE.md`,
`rule_option_entropy_prior_v0.md`, and the existing simulation-dominance,
capture-resource-persistence, exchange-survivability, and hand-resource
closeouts. No human-value tables, new validation metrics, or Xiangqi material
values were consulted to prepare this comparison.

## Current local Agent route

This comparison is historical research evidence, not a gate awaiting a
Supervisor or user choice. Under `AGENTS.md` and `LOCAL_MAINLINE.md`, the sole
local Agent selects bounded scientific tests and revises the route as evidence
changes. `ROOT_DECISION_IDENTIFIABILITY.md` shows that even a fixed, labelled
root can leave material ratios and the cardinal unit unidentified;
`RESOURCE_CONVERSION_UNIT_CHECK.md` rules out treating legal conversions as
cost-free exchanges. `INITIAL_CONTEXT_COVERAGE_CHECK.md` shows that the Chess
initial position alone leaves three ordinary types without an immediate
action. The live route is in `LOCAL_MAINLINE.md`. Xiangqi material values
remain an untouched holdout. Publication and promotion follow the current
policy's test, diff inspection, and remote verification conditions.
