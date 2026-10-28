# Exact evaluation, fixed-frontier stability, and completed-depth quality

This bounded AUX method check separates two statements. An exact evaluation
transformation preserves a fixed finite backup objective. A more deeply retained
heuristic iteration need not choose the better terminal branch. Neither is a
new Leaper strength measurement or a reason to reopen the closed cost study.

## A concrete uniform bound for the new representation counterfactual

The source/UNUSED pair in AUX_STATIC_MASK_CONSUMER_20261029 has unchanged actual
movement and reachable-game mechanics under an explicit action/history mapping.
Its semantic default tables differ by A393, B400, C171, K0. Initial per-owner
inventories are A3, B3, C2, K1. Captures remove enemies from the game; movement
preserves owner and type. There are no promotions, drops, creation, triggers or
hand production. Thus each owner's count of each old type can only decrease.

Let n_ot be the current count owned by o of type t. On related positions the
difference between seat0 material terms is

`D = 393(n_0A-n_1A) + 400(n_0B-n_1B) + 171(n_0C-n_1C)`.

The dynamic terms cancel because their geometry, positions and weights match.
UNUSED remains absent. Since each count lies in its original owner/type box,

`|D| <= 3*393 + 3*400 + 2*171 = 2721`.

The final side-to-move sign does not change the absolute bound, and the search
static clamp is1-Lipschitz. An independent enumeration of all2304 material-count
box allocations attains the algebraic extrema+/-2721 and checks the arithmetic.
Those allocations are not generated or solved board positions; reachable
attainment of the bound is UNKNOWN. The actual legal nonterminal witness has
absolute difference171, not2721. No hand-price or WDL quantity is inferred.

This is a structural uniform difference bound for THESE TWO surrogate tables
on THEIR shared reachable-game domain. It is not an approximation-error bound
relative to optimal play, and not a global statement about all Generic rules.

## What min/max backup can preserve

Fix a finite tree and its cutoff frontier, including the same terminal payoff
and path-distance treatment. If corresponding leaf values differ by at most
an epsilon in absolute value, every backed-up node value differs by at most
epsilon. The proof is induction: both min and max are nonexpansive in the sup
norm, so an internal error is bounded by the largest child error. Alternating
negation has the same property. No sampling or independence assumption is used.

For a fixed root action set this gives two useful sufficient statements:

* If the old unique best action exceeds every alternative by strictly more than
  2epsilon, its identity remains best under the perturbed leaf function.
* If the selected action changes, its loss measured using the OLD fixed-tree
  surrogate is at most2epsilon, by applying the two endpoint inequalities.

For the source/UNUSED example epsilon2721 gives5442 in those score units. We do
not have all saved root-action values/gaps, so no particular real root is
certified by this criterion. The bound is not terminal regret, win probability,
Elo or evidence that a price is strategically correct. It adds no mandatory
proof, calibration or experiment-admission gate.

For the exact mask transformation epsilon is0 relative to its fixed reference
instance. Fixed-tree backed-up values therefore coincide. If a tie policy or
visited frontier changes, action/PV identity requires its own conditions. The
actual archived ablation separately checked equal actions/PVs/work. The theorem
does not cover a different retained depth, incomplete or bounded return,
unmatched q/extension semantics, incompatible warm TT entries or a changed
service allocation. In particular, the earlier warmQ4/D1Q0 counterexample is
not repaired or contradicted by a fixed-frontier theorem.

## Actual mainline return control on one declared toy game

The full abstract tree is root R, with two actions A and B. Each branch then has
two forced actions. A's final terminal awards player0 a win; B's terminal awards
player1 a win. Actors alternate at every edge. This is an explicitly defined
finite abstract game, not an executable Leaper RuleSet or a Core-certified label.

One UNCHANGED seat0 heuristic assigns:

| Node | A1 | B1 | A2 | B2 |
|---|---:|---:|---:|---:|
| h |10|0|-10|10|

At a leaf the actual evaluator returns the appropriate actor-centric sign.
TT, ordering, root tactical scan, optional pruning and ordinary/hard Q are OFF.
The actual committed run_root_search/negamax state machine is called through a
small declared runtime adapter; the mainline implementation is not copied.
All calls request maximum depth3. Explicit cooperative stop signals are set by
its real progress callback after completed iteration1 or2; the third call has
no such stop. These are not equal-time or equal-node budget experiments.

| Retained depth | Returned action | Score | Actual return source | Declared eventual winner |
|---|---|---:|---|---:|
|1|A|10|main_iteration, cancelled|0|
|2|B|10|main_iteration, cancelled|1|
|3|A|999999997|main_iteration, completed_depth|0|

All three calls restore the abstract path and have zero Q nodes. The completed
D2 result is legally retained by the source state machine even though that
choice is worse under the TOY's terminal definition. The same static evaluator
at every queried state is compatible with the deterioration: changing depth
changes the frontier. A hypothetical exact implementation improvement does not
supply a missing guarantee about the newly reached frontier's relation to true
payoff. No speed was measured or simulated, and this is not evidence that the
real mask worsens play or that deeper search is usually worse.

Three standalone control calls plus the three executed by its one regression
case were made before this report's closing ledger. These are actual abstract
search executions, not zero computation and not new Player/game/Native studies.
The other static-contract tests perform compilation/evaluation/Core operations;
their aggregate primitive counts are UNKNOWN. The control need not be repeated
on more toy trees to establish this existential counterexample.

## Original research source and what is not transferred

[Nau1982, An Investigation of the Causes of Pathology in Games](https://www.cs.umd.edu/~nau/papers/nau1982investigation.pdf)
analyzes a probabilistic Pearl-game model and contrasts an incremental model.
It demonstrates that better local information near the end need not imply
monotone decision improvement under minimax, and discusses dependencies among
related positions. Its model-specific probability calculations are not an
estimate for GenericChess. Our forced-chain example is a simpler existential
construction, not a reproduction of those results or their stronger conditions.

Selected introduction/model/decision definitions and sections5/6 were read.
The22-page original PDF is privately pinned, SHA256
`a76843a0b966682d3b6908dfb5c5e98edc51ff72b16a1e7188f57e3e3e39e688`.
No paper source is republished, no Monte Carlo or alternative minimax algorithm
was run, and no historical engine recommendation becomes a new task. No IID
rule distribution, pathology frequency or chess-to-Leaper transfer is inferred.

The practical consequence remains the current GitHub Pro priority: finite
cost/retained-depth diagnostics are useful, while claims of decision improvement
need their own declared actual evidence. This does not require exact WDL before
every useful small experiment. PRIMARY owns its new frozen quality study;
AUX has not launched it or supplied a new default.

[Structural bound](data/aux_static_mask_consumer_20261029/uniform-value-bound.json.gz)
and [actual abstract returns](data/aux_static_mask_consumer_20261029/depth-quality-control.json.gz)
record assumptions separately from the original archived Leaper data.
