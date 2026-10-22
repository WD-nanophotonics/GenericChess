# Pure-Leaper forward design: codebook and first competence portrait

2026-10-22. PRIMARY_SANDBOX; exposed finite pilot, not a learner, population
estimate, solved-game benchmark or production-default change.

The user confirmed the latest ChatGPT comments as the new direction after the
already registered work closes. The useful immediate question is whether small,
explicit rules distinguish cheap controllers at a measurable cost. The older
common-Unit-order material ablation remains NOT RUN/deferred; its frozen inputs
and historical evidence are preserved. General rule semantics, including future
promotion/drop/history work, remain the long-term target. This pilot deliberately
uses a smaller declared domain.

## Frozen setup

A 4x4 board has one King-like Anchor and one each of ordinary A/B per side.
Player 0 starts K a1, A b1, B a2; player 1 starts K d4, A c4, B d3. Side0 moves first.
Every ordinary move is a Leap; capture removes, no drops/promotions/rays or new
auxiliary rules. Core/GameSession retain complete histories, real repetition4
and rule max_ply128. The caller also observes128plies: a real rule terminal at
that boundary takes precedence; caller/whole-run censoring would remain UNKNOWN.

D4 orbits are O1=(1,0), O2=(1,1), O3=(2,0), O4=(2,1), O5=(2,2), each expanded to
all signs and coordinate swaps. A nonempty five-bit mask selects their union.
All 31 masks are distinct and symmetry closed. The exact empty-board component
sizes are O1:16, O2:8+8, O3:4+4+4+4, O4:16, O5:eight pairs. These describe one
piece's movement graph, not closed game classes or learnability.

Ten mask pairs were selected before outcome queries: (1,2),(1,3),(1,4),(1,8),
(1,16),(2,4),(2,8),(4,8),(8,16),(3,8). Quantity/layout stay fixed; no failed or
unfavorable member is replaced. All ten round-trip the strict RuleSet schema,
compile, and have legal nonterminal starts.

Controllers are existing Static AlphaBeta at node512/maxdepth64, ordinaryq0,
forced-check limit8; uniform Core-legal Random; and FLOOR, choosing the first
actual one-ply winning child, otherwise uniform over all legal children.
Static uses the complete default profile, including dynamics: this is NOT a
material-only/no-prior evaluator. Actor TT is fresh per game and persists inside
that game; disk cache OFF. Full returned search diagnostics are retained.

The pilot has60 NEW physical games:10rules x3controller pairs x2candidate roles.
A separately frozen continuation adds seven NEW seed repetitions for all ten
rules,420physical games, not a replacement or cap refill. Candidate/opponent
streams are explicit per actor/world/role/repetition and matched across pairs;
diverging actions change future positions. There is no human-label fit, oracle
opening selection, training or cross-checkout work.

## First forward portrait

All 480 executions finish with real rule terminals,0callerUNKNOWN. Each controller
pair has160role frames. Signed utility is win+1/draw0/loss-1.

| Controller versus Random | W | D | L | Signed mean |
| --- | ---: | ---: | ---: | ---: |
| Static AB512 |64|96|0|2/5|
| FLOOR |14|144|2|3/40|
| Random |1|156|3|-1/80|

The observed paired AB–FLOOR mean is13/40; AB-Random is33/80. These are finite
contrasts on these exposed rules/seeds, not sampling confidence intervals or a
universal algorithm ordering. Seat/seed pairing is retained, not normalized away.

| World | A/B masks | AB512 mean | FLOOR mean | Random mean |
| --- | --- | ---: | ---: | ---: |
|0|1/2|7/16|1/8|0|
|1|1/3|3/4|1/4|-1/16|
|2|1/4|1/2|0|0|
|3|1/8|9/16|0|0|
|4|1/16|1/8|0|0|
|5|2/4|0|0|0|
|6|2/8|11/16|0|0|
|7|4/8|1/4|0|0|
|8|8/16|0|1/16|0|
|9|3/8|11/16|5/16|-1/16|

Keep worlds 5/8 as negative controls. World 8 has an observed FLOOR win while AB
always draws. No rule is declared intrinsically bad or solved. The480 terminals
are255max-ply draws,98repetitions,84checkmates,43stalemates. Long rule-clock draws
are not caller censoring or evidence of a search bug.

There are48,176controller-turn receipts but only7,325AlphaBeta returns. RNG/FLOOR
choices are not Player queries. AB takes all64 observed immediate-win opportunities
and never selects an immediate opponent-win reply when a safe child exists in
the checked finite roots. This does not prove a forced WDL beyond those witnesses.

Physical work and independent evidence differ:480 executions represent331distinct
complete GameRecords,30,779distinct full root GameStates and160world/role/seed
cells. FLOOR and Random have identical full trajectories in147 of 160cells;
AB differs from both in all160. Repeated histories are not independent learning
opportunities. Process/cost records retain captures, legal counts, repeated
physical positions, complete-state counts and actual search depths/sources.

The first60games take291.179seconds and the420new-repeat games1746.950seconds,
including their producer recording. Search/choice times and recording/generation
costs remain distinct. These clocks do not include all source engineering or
publication time and are not a universal wall-cost bound. Existing concurrent
project load is an interpretation limit. No exclusive timing window is requested.

## Structural coordinates are not bounded-policy equivalence

The961 ordered mask pairs have496 representatives under the declared diagonal
reflection plus A/B relabelling of THIS layout. All496 initial legal-action
mappings and47 selected complete root-child mappings pass. This is a declared
structural quotient, not a minimal semantic quotient or full game-tree certificate.
Keep the execution fingerprint, ordered masks, actual layout and version.

Twenty complete-history cost-screen roots have matched reflected/relabelled
histories. Reusing20 original512node returns and adding20 NEWtransformed returns,
four selected physical actions change although measured depth/score agree. Those
four are world2initial,world3midprefix,world4midprefix,world7initial. Returned PVs
are legal. No selected-action WDL difference is claimed. Do not transfer a finite
policy's performance to every representative merely because the game structure
has a symmetry. Canonical execution or an explicitly symmetry-averaged protocol
would be needed for such a performance coordinate.

## A fastest-win objective has a concrete degeneracy

A complete initial root/one-ply census finds123 of 496 representatives with an actual
immediate win. Under uniform independent nonempty ordered masks the corresponding
count is240/961. Structural-class-uniform and ordered-mask-uniform are different
laws. Exact Random initial-win probability under the latter is425113/13319460;
FLOOR's is240/961. These are finite one-ply probabilities, not whole-game strengths.
All ten predeclared pilot pairs have zero initial wins; they were not chosen using
this later census.

For masks(1,11), B a2-b3 is Core checkmate with zero legal defenses. The complete
rule and one-action GameRecord are retained. Optimizing only quick wins would
reward such trivial tasks. Preserve a multi-dimensional rule-to-performance
portrait and cheap negative controls instead of calling a fastest-win scalar
"good game". No optimizer or sampling filter is activated here.

## Recovery and qualification

The first preparation attempted a nonexistent CompiledRuleSet.fingerprint field:
10 setup failures,0Player queries; canonical inputs and failure were preserved.
The schema's compute_fingerprint(RuleSet) is the correct API.

The first60 actual games then hit a terminal aggregation error: SessionResult has
no Core TerminalResult.is_terminal property. All action/decision returns had
already been saved. A pure replay reconstructed all 60outcomes and validated
6,217historyplies/4,220literal PV edges, with zero new Player calls. Original
failed receipts remain private; the technical copy marks the recovery and omits
actual private-path traceback strings. No fitness game was rerun and no expected
product test value was changed. The corrected probe has29contract tests covering
real session statuses, unknown versus draw, strict masks, analytic components,
canonical rules and legal action matching.

## Matched node-budget and material follow-ups

Twenty NEW node2048 games use the exact pilot rules, roles and initial actor
RNG seeds. The matched512baseline is7W13D, not the8-seed aggregate. The new
policy gives9W11D: finite signed effect+1/10. World0role0,world6role0 and
world7role1 improve; world2role0 regresses from win to draw. Keep that negative
case. A larger node budget is not an optimal-strategy ladder or universal gain.
Actual runner time is1107.104seconds, within the original1800second cap; the
complete-history cold-call forecast was1350seconds. Separate decision-node and
choice-time totals remain in the paired comparison; do not compare whole-run
time to the baseline's inner-choice clock as if those denominators were equal.

Forty NEW material-follow-up games use the SAME three-method Adapter on both
search arms, common Static ordering,512nodes and the same ten rules/roles/pilot
seeds. Static leaf gives7W13D; M0 gives4W16D. M0-minus-Static is-3/20. Static's
extra wins occur at world1role1,world2role1 and world3role1. All20 Static-Adapter
complete records match the earlier default-path records; that is observed here,
not an all-domain adapter equivalence claim. Static/M0 complete trajectories
agree in only1of20cells, so changed actions alone would greatly overstate utility.

M0 zeros CURRENT-board and BASE-hand material only. Median, promotion data and
dynamic weights stay intact, and ordering still carries Static prices. It is
not no-prior/price-free search or an optimized learned alternative. Forty actual
opening/natural-prefix calls and151root/child feature checks establish the exact
Static-minus-M0 material decomposition in the saved states. The max-call forecast
is508.069seconds; the actual40-game run takes509.648seconds, within1500seconds.
This finite marginal material effect is compatible with other negative Unit/
Static envelopes and gives no TD training-gain theorem.

The reusable CLI's material preflight now requires frozen nonempty full-history
inputs and actually measures both Adapter policies, not defaultAB. A missing
record fails before a cost query or successful receipt. Cost/decomposition gates
are enforced before fitness. Actual older execution sources are preserved in
the technical packet; no completed fitness is rerun for this caller correction.
Thirty-two relevant probe contract tests pass.

## User-confirmed next direction and begun next step

After the registered runs closed, the latest ChatGPT21:11message and relevant
Claude21:49thread were read and privately saved in full again at the user's
request. The user explicitly confirmed ChatGPT's direction here. Its pure-Leaper
forward-design/inverse-design route now supersedes older optional backups in
AGENTS/current Main. PRIMARY owns generation/cheap evaluation; existing DEV_AUX
owns bounded truth/learning. No outgoing messages, new workers, default changes,
AUX checkout writes, or schedule changes occurred.

Claude's proposed Random ceiling is not triggered: none of the ten rules has AB
score>=0.95; the maximum score is0.875. Structural forecasts cannot be retroactively
predeclared for these measured data. Single-piece connectivity is not whole-game
WDL. Do not assume a six-piece history-conditioned graph is cheaply solvable.
The earlier fixed-temperature, unfitted proxy ranking flip does not compare
calibrated predictors or refute learning; optional scale fitting remains deferred.

The NEXT cohort is actually prepared, with ten cold calls but zero fitness games.
A fixed RNG seed samples ten classes uniformly without replacement from the486
remaining sorted mask pairs, without outcome filtering. Complete inputs, budgets
and motion-only ordinal forecasts are frozen BEFORE those first new Player calls.
The forecasts predict larger AB-minus-Random advantage and decisive fraction
from larger summed empty-board mobility; tied-rank/all-ten analysis is specified
in advance. AB-minus-FLOOR and initial-one-ply-win strata are separate diagnostics.
No fitted coefficient or optimizer is introduced.

Masks are(11,26),(9,20),(9,23),(4,20),(7,26),(13,26),(16,24),(11,14),(24,26),(4,10).
Planned60games, expected900seconds/cap1800; the measured preflight forecast is
529.168seconds and passes. Full root/one-ply metadata was already exposed by the
codebook: this is gameplay-new prospective validation, NOT a strict unseen-rule
or unseen-initial-label holdout. No old UNKNOWN/cap is refilled. Science OPEN.

## Technical delivery

The compact packet at[data/leaper_forward_design_20261022](data/leaper_forward_design_20261022/README.md)
contains540NEW physical executions,53,728controller-turn receipts and10,104actual
AlphaBeta returns, with complete rules/records, returned diagnostics and executable
source snapshots. Current-stage cold calls total120; the prepared next step adds
10NEWcold calls and0fitness games. Reused cost references are not extra queries.
It is8,695,253compressed bytes/78,202,940decoded bytes; SHA-256
`65cbda6e861249f04914511f5bcdd1e83233879c276236df7caac1f7d5c0b761`.

The actual exported-copy reader passes on all540games:53,728history plies,
43,814literal PV edges,35,498RNG stream checks and8,126FLOOR policy checks.
It takes161.632seconds. These checks establish retained execution/serialization
and declared-controller fidelity using shared Core, not independent game WDL.
The required publication gate and full remote SHA are checked separately.
