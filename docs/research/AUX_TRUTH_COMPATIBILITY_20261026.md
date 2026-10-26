# Source-bound complete-history and partial action truth consumer

Current status: PRIMARY's new frozen candidate input is still
`AWAITING_FROZEN_INPUT`. Old exposed H6 records below are consumer controls,
not a substitute candidate panel or new held-out evidence. This AUX work does
not generate rules, tune search, run a Player or solve new truth.

The latest direct user correction authorizes this existing support work without
another approval question and requires an actual60+effective-minute work segment.
The earlier prelaunch approval stop is superseded; cumulative prior112.346442
minutes remain recorded separately from the new work. No old frozen run is extended.

## Actual implementation and evidence

Shared runtime is reused from sandbox
`578cd42b0672181dafa4f0bdb8015be109bd4cdc`. Only existing AUX learner differences
remain independent. Infrastructure availability is not measured acceleration.

`scripts/leaper_truth_compatibility.py` binds full semantic RuleSet, canonical
GameRecord, complete GameState/history/repetition counts, clock, setup, current
turn and Session outcome. Exact conservative identity is the default engineering
contract, not a theorem that every raw serialization byte must always match.
Metadata prose is excluded from semantic identity; proven scoped transformations
would need their own checked preconditions and are not automatically accepted.
A geometry signature, board match, root WDL match or one legal PV cannot replace
that contract. Session resignation/declaration and Core terminal are distinct.

Separate outputs describe compatibility, what was actually checked, and action
coverage. A hash/source match attributes labels but does not verify minimax truth.
The corpus reader literally replays3616published fresh roots under11available
full RuleSets and checks10936/10936legal source action labels. Family0 remains
`UNKNOWN_MISSING_RULE/MU_UNAVAILABLE`. No missing family or initially refused
setup is replaced. Source H6/repeat2 cannot label H128/repeat4.

The saved-tree consumer checks an existing full-state certificate against Core:
every supplied state, exact legal frontier, child transition, rule terminal and
local max/min label equation must agree. Missing nodes/defenses are rejected,
not solved. On the existing history packet it checks20trees,168nodes,148edges,
134terminals and10same-Position/clock history pairs. The history pairs remain
incompatible for direct label reuse. This is proof checking on supplied finite
objects, not a new minimax search or a new scientific witness.

## Partial truth and sharp bounds

Values are -1/0/1 relative to an explicit fixed seat. Convert to the current
actor before comparing choices. Unlabelled actions retain[-1,1]. Root bounds
and action bounds are different claims. Inconsistent claims are rejected.
An action with a WIN lower bound attains the WDL ceiling despite unknown
alternatives; a nonloss[0,1] bound does not establish exactDRAW or optimality.
A qualified exactDRAW root plus a nonloss action does establish WDL optimality.
At an exactLOSS root every legal choice is WDL-optimal, even though all lose.
A sole legal action is optimal without determining its value.

For actor-relative intervals[L_i,U_i] and root bounds[A,B], feasibility requires
max(L_i)<=B and max(U_i)>=A. Clip each upper bound atB. Raise actioni's lower
bound toA only if every other action has upper bound belowA. These projections
are sharp: every retained endpoint has a feasible completion.
The exact one-decision regret interval fori is
[max(0,A-U_i,max_other(L_j)-U_i), max(0,max_other(U_j)-L_i)].
A sole action has regret0. Zero upper regret proves optimality; positive lower
regret proves suboptimality; otherwise the classification remainsUNKNOWN.
These statements concern attributed WDL bounds, not mate speed, heuristic score
or opponent-specific win probability.

For two actually selected actions in the same context, the consumer reports
sharp candidate-minus-baseline value bounds. The same action cancels to[0,0]
even if its value is unknown. A different unlabelled action remains uncertain;
these are finite one-decision bounds, not an Arena result or confidence interval.
Exhaustive literal completions for1â€“4actions check the interval formulas and
seat reversal, with separate paired-action completion checks.

## Label-count information diagnostic

We enumerate every exact-label subset on all39value-multiset patterns present
in the3616old source frontiers, with root counts retained. This is a hypothetical
information budget: one label is not a measured unit of certificate cost.
Every pattern's exhaustive result also agrees with an independent closed form.

Forn>1, letm be the number of actions aboveLOSS andk the number attaining the
known true maximum. With the root value unknown, one optimal action needs one
WIN label if aWIN exists; otherwise it needsn-1labels whenm<=1, andnlabels when
m>=2. Classifying every action needsnlabels. With an exact root supplied,
aLOSS root needs0action labels; other roots need1label to identify an optimal
action andn-1labels to classify all only whenk=1, otherwise n. A sole action
needs0labels in all cases. Lower bounds follow by assigning adversarial values
to any omitted labels; these are identifiability statements, not label acquisition
policies or permission to inspect oracle labels when selecting training starts.

On the existing corpus, an exact root allows an optimal choice to be certified
with0action labels at696roots and1label at2920roots. Without root truth the
minimum histogram is0:488,1:928,2:960,3:744,4:376,5:112,6:8. These counts do not
choose a new PRIMARY panel and do not establish useful difficulty or search gains.
Coverage fraction alone therefore does not determine decision identifiability.

## Collaboration and limits

GitHub Pro183742at the source above is adopted for AUX role/scope. Solicited
Slack Dot reply1793009276.470739 independently read reports only; its advice to
separate compatibility/qualification/coverage and retain partial bounds was
adopted and implemented. It did not execute the new consumer or approve scope.
The new user instruction, not that reply, resolves the old repeated-approval stop.

No new Player, solver, game, build, candidate generation, H6syntax cache iteration,
1520return rerun, production default, PRIMARY state write or scheduler change.
Actual source data remain exposed controls; missing PRIMARY inputs stay explicit.

Current concrete milestone is published while the research segment remainsACTIVE;
this is not a60minute completion claim. End-to-end CLI:
`python -m scripts.qualify_leaper_candidate_truth --candidates INPUT.json --output OUTPUT.json`.
INPUT is an explicit list of{id,rule,record,selected_action(optional)}. No input
is auto-generated. The preserved historicalPRIMARY p53record lacks a complete
RuleSet in its own envelope and correctly returnsUNKNOWN; the consumer does not
guess a rule from its name or borrow H6 labels. Resignation mismatch returns
INCOMPATIBLE with no action coverage.

Source pins and compact results are in[data/aux_truth_compatibility_20261026](data/aux_truth_compatibility_20261026/).
At this milestone124relevant headless checks passed, including38newsemantic checks.
