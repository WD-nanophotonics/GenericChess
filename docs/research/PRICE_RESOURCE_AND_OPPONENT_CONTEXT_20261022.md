# Price, resource and opponent context — 2026-10-22

The new rules support a conditional Unit-leaf advantage, rather than a universal
price winner. Its effect changes with the opponent and search allocation.
Shallower ordinary q search is a useful development control; skipping q also
remains competitive under actual node budgets. Keep Static and Unit candidates,
the complete rule semantics and all UNKNOWN outcomes. No production evaluator,
search default, generator filter, learner, API or AUX checkout changes.

## Fresh inputs and fixed opponents

Twelve configurations were fixed before generation: 4/6/8 boards, classic/free
setups and bilateral/unrestricted movement, with new seeds and a 16-attempt cap.
All succeed. The opening-win preference is ON only for this local experiment.
This is a generated legacy-movement subset executed through the semantic compiler,
not a claim covering every auxiliary/custom rule or independent mechanism holdout.
Every declared/future type, promotion, drop and full history is retained.

Both leaf candidates use Static material-order inputs and dynamic weights 2/5/3.
Unit supplies CURRENT-board 1000 and BASE-hand 900, anchor zero, preserves supplied
proved-inert hand zeros, and removes price-derived promotion gain. This is a
complete leaf-price policy, including that bonus, rather than one coefficient.
Each actor has its own fresh Player/TT per game; the TT persists within that game.
Disk profile caching is OFF. TT/history ordering remains endogenous to each policy.

FLOOR chooses the first Core immediate rule win, otherwise a uniform legal action
using its registered owner RNG stream. All 48 new games finish within the frozen
96-ply observation cap. Static has 21 wins/3 losses; Unit has 21 wins/2 losses/
1 actual stalemate draw. Unit minus Static utility is exactly **1/24** on 24 role
pairs. Only two outcomes differ: loss to win and win to draw. This is utility
(+1/-1/0), not a win-rate percentage or population confidence interval.

The next experiment fixes a Static D1 search opponent, rather than changing both
players. A = Static D1, B = Unit D1, C = Static requested D2/q4, D = Unit requested
D2/q4; C1/D1 below denote Static/Unit requested D2/q1, not a depth-one label.
All use common Static material ordering, 8192 total nodes and a one-second decision
limit. There are 84 new four-cell games plus 48 q1 games. Twelve A self games are
reframed as both roles, giving exactly opposite utility, including UNKNOWN.
Other continuing-policy UNKNOWN tails are independent, even for identical prefixes.

| Contrast against the same fixed Static D1 opponent | Finite utility bound |
| --- | --- |
| Unit D1 minus Static self baseline | [1/3, 7/12] |
| Unit minus Static, requested D2/q4 | [1/24, 17/24] |
| Unit minus Static, requested D2/q1 | [-1/4, 5/12] |
| Static q1 minus q4 | [1/24, 19/24] |
| Unit q1 minus q4 | [-1/6, 5/12] |
| Price/requested-depth interaction | [-13/24, 3/8] |

A separate enumeration of 118 endpoint assignments verifies all 11 reported
aggregate, per-configuration and role bounds. Unit D1 remains positive after
omitting any one configuration; the other positive contrasts do not. These are
posthoc sensitivity checks, not selection rules or new statistical guarantees.

The aggregate price/opponent interaction is [7/24,13/24], yet individual rules
reverse: rule 4 gives Unit +1 against FLOOR but [-1,0] against Static D1; rule 7
changes from -1/2 to +1. Do not use a favorable weak-opponent result as a per-rule
price label, filter or universal advantage. No oracle-selected training occurs.

## A concrete budget and reserve mechanism

On rule 4, the first Static/Unit divergence is at ply 2. The Static D1 action
allows one fully enumerated opponent immediate checkmate; Unit's action does not.
This explains the local FLOOR difference without claiming the alternative is
perfect-play winning. The other changed outcome has no such immediate-loss witness.

Configured positive q depth temporarily reserves ordinary q0 for the first main
iteration, while still extending forced checks to hard depth 8. Requested D2/q4
retains that D1 choice at one and two seconds. The one-second Static return pays
85 main plus 2619 q nodes: 85 is not its total work. q1/q2 finish D2 and avoid the
exhibited immediate loss. Configured q0 with the default check-only switch OFF
skips q entry, including forced-check extension; it is a different control.

Sixteen separate cold fixed-node controls remove deadline effects. Static q1
finishes D2 in 1214 counted visits; Unit uses 886. Full q4 needs 34673/20511,
respectively, and both finally select the same P drop at stored coordinate (3,2).
Thus the price-dependent completion cost can differ even when the completed
choice agrees. These are scoped heuristic-search results, not all-domain scalar
minimax or WDL proofs. All 32 cold depth/q/node controls have separate Core/PV
qualification; their returns are not counted as additional games.

Search visits are not all semantic work. Complete Static q4 uses 107811 successful
runtime pushes, including 28159 nonchecking drops classified out. Unit uses
58344 pushes. Making all three already-timed legal-generation/evaluation/ordering
blocks free would still leave 10.48/5.65 observed seconds on those traversals.
This is scoped accounting, not a hardware-independent lower bound or an estimate
of a proposed runtime optimization. PRIMARY does not take over AUX runtime work.

A new one-field capture intervention legally replays the same actual history.
Only fingerprints and legitimately reconstructed hands differ in the current
position. Frozen pocket board/gain/order prices remain explicit caller inputs.
Pocket Static q4 uses 34673 nodes; zeroing only its hand leaf values increases this
to 48722. Capture-to-remove uses 9019 with either hand profile, with identical
scores, choices and work counts in that empty-hand negative control. Six new
queries and two exact source reuses pass a separate full-history/PV reader.
This changes the rule and legal/resource/payoff context, not merely runtime cost;
it is not a same-RuleSet board-only-value impossibility or a hand-zero default.

## Actual node allocations and the missing direct rung

A new common-opponent curve fixes Static/q1 at 1024 visits and allows the candidate
1024/2048/4096 main-plus-q visits, maximum depth 64, with no decision deadline.
Sixty physical games supply 72 role frames; self games are exact role reuses.
Twenty-four further q0 games use 2048 visits against that same 1024/q1 opponent.
All slots are retained, with no cap refill or generation replacement.

| Common-opponent contrast | Finite utility bound |
| --- | --- |
| 2048/q1 versus 1024/q1 self baseline | [1/3, 7/12] |
| 4096/q1 versus 1024/q1 self baseline | [1/2, 3/4] |
| Their effects against 1024: 4096 minus 2048 | [-1/12, 5/12] |
| 2048/q0 minus 2048/q1 against 1024 | [0, 1/3] |

The third row is **not** a direct 4096-versus-2048 match. A separately registered
24-slot direct comparison supplies that missing rung: **[1/6,1/3]**. All 24 games/1016 returns pass Core replay/PV checks.
Higher budget loses both seats on rules 0 and 7, so positive aggregate rungs do
not establish per-rule monotonicity.
Do not call requested/completed-depth mixtures a fixed-depth pathology theorem.
These remain particular budgeted algorithms, not optimal resource-bounded strategies.

q0 pays 260.20 candidate seconds versus 363.41 for q1 at 2048, and 946885 versus
1151476 candidate visits over the observed prefixes. That is an observed-prefix
cost frontier, not automatically a full-game cost claim. A conservative analytic
512-ply continuation bound leaves q0-versus-2048/q1 full counted-node cost uncertain.
Against 4096/q1, q0's full candidate-node upper bound 1798853 is below that arm's
already-paid 1999508, even if q0's one UNKNOWN uses all 416 remaining plies itself.
The gap is 200655 counted candidate visits. Its utility difference remains
[-1/6,1/6]. This bounds neither wall time, primitive transition work nor both
players' total cost. No continuation beyond the frozen 96 plies is executed.

## Interpretation and reproducibility

The earlier report already records requested D3 as 193 actual D3 returns,
117 D2,103 D1 reserves and10 immediate wins, and excludes a general pathology
claim. The new Claude comment usefully reinforces that distinction; it does not
invalidate those counts. Its AUX prior/training proposals stay in AUX's lane.
SPRT, SPSA and release migration are not adopted as policies or new work here.
There is no outgoing Chat message, @mention, live contact or response polling.

Theoretical minimax pathology concerns the relation between search and decision
quality under specific models, rather than a requested-depth label. The primary
real-valued model also makes error/distribution assumptions not established for
our prices. [Nau's publisher abstract](https://www.sciencedirect.com/science/article/pii/0004370282900029),
[Heinz's fixed-iteration experiment abstract](https://dspace.mit.edu/entities/publication/c8afb014-af0b-42d1-81ac-9d9861b6860c),
[Luštrek et al.'s author manuscript](https://dis.ijs.si/mitjal/documents/Independent-valued_minimax-Pathological_or_beneficial-TCS-12.pdf).
The saved reading notes distinguish accessed sections and unavailable full text.

The exact technical [capsule, summary and reader](data/price_resource_and_opponent_20261022)
retain full inputs, raw decisions, histories, failures, costs and harness sources.
Base public-copy qualification covers 264 games,10342 physical plies and14467
literal PV edges; adjacent-rung coverage is 24 games/1016 physical plies/2530 PV edges in a separate phase.
It uses the shared Core, not an independent rule implementation or proof of every
q scalar/all-defense value. Original private reads and all unique evidence remain.
Raw Slack/account/session/approval logs and personal information are excluded from
publication. Product source and old test assertions are unchanged. The mandatory
publisher runs the related benchmark/declaration regression targets and verifies
the full remote SHA; a local commit alone is not delivery.

Next, 12 NEW full unfiltered-generator inputs and complete Static/Unit profiles
are prepared, with zero Player queries. The question is whether the leaf contrast
survives node2048/q0 against fixed Static2048/q0 on that new scope. Configurations
were fixed before generation; all succeed, with no replacement. Removing the local
opening preference and changing the search envelope together is not an isolated
filter-effect experiment. No future game has started and no default is selected.
Science OPEN.
