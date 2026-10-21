# Finite roster laws and semantic attack authority

PRIMARY_SANDBOX, 2026-10-21. These are bounded diagnostics of rule-only prices
and unfamiliar-rule search. No model, default evaluator, generator setting or
search policy is promoted. No human labels, auxiliary checkout or new worker
was used. Protocols, actual rules, records and executed programs are in
[`data/finite_roster_20261021/`](data/finite_roster_20261021/).

## Count conditioning changes a model, but does not earn implementation

The first question was whether conditioning an occupancy model on finite piece
counts can change relative opportunity rankings rather than simply rescale them.
For an occupied actor source, A assumes independent remaining occupancy and
balanced enemy probability; B corrects the enemy marginal for that known own
actor; C distributes the actual fixed friend/enemy/empty counts uniformly
without replacement. These are distributions over geometry, not game values.

Seven leap/ray/screen templates, six board sizes and every registered equal
roster give 140 count settings and 2,940 type-pair comparisons. Exact rational
arithmetic finds A/B:3, A/C:11 and B/C:8 strict ranking reversals. Ten A/C
reversals remain on boards >=4; one 3x3 case is outside the current generator.
Ten of the eleven involve a cannon. The largest screen/ray ratio change is
8.87%, on 3x3. Existing independent-occupancy analysis agrees to 7.11e-15 and
the semantic cannon control agrees to numerical precision. Independent full
3x3 enumeration checks 9,072 source/occupancy configurations across all templates.

The follow-up used six *different*, prespecified generated substrates, given a
cannon recombination, and four uniform legal trajectories each, capped at40
plies. All24 slots complete; 804 ongoing states provide6,251 cannon-actor
observations. The complete records retain178 drops and42 promotions, with no
legal-target subset discrepancy and matching full-history replays. This sample
does not exercise every auxiliary/history mechanism in the generic target.

MAE is A:1.753479, B:1.756879, C:1.752056. C improves over B by only0.2745%
pooled (0.4341% with equal rule weighting), although four of six rules improve.
The preregistered5% improvement gate fails. **Do not implement a count-law
correction from this result.** This closes that inexpensive approximation under
the tested distribution, not all occupancy laws or static prices. Observations
are correlated and no opportunity error is interpreted as a WDL/price error.

## Existing semantic authority changes actions, without demonstrated utility

A separate prospective64-slot panel used eight new generated substrates with
the same cannon construction, prefixes3/4, both candidate owners, and a fixed
legacy-evaluator opponent. Only candidate attack authority differs: existing
`Evaluator` versus `SemanticAttackEvaluator(backend='native')`. Both arms use
identical Unit board/hand tables, zero promotion gain, dynamic coverage2 and
anchor heuristic5. Limits are D3,2,048 total nodes,50ms, q0/hard-q0; TT,
ordering and root tactical scan are off. The game cap is48 additional plies and
the whole-run cap300s. Equal configured budgets are not equal actual work/depth.

Four recombinations fail initial-anchor safety before play:32 slots remain
failed/unstarted UNKNOWN, with no replacement seed or repaired initial setup.
The other32 games yield27 actual checkmates and5 capped ongoing outcomes.
The whole run closes in28.09s. All64 registered keys remain unique; an independent
reader replays all32 actual records and654 actions with matching results.
All8 feasible root map checks agree between Core and Native; the8 infeasible
planned roots were not checked or silently counted as successes.

Semantic-minus-legacy reward bounds, treating each UNKNOWN as[-1,+1], are
**[-1.0625,1.25]**, owner0[-1.125,1.125], owner1[-1,1.375]. These are conservative
finite accounting bounds, not statistical confidence intervals. The retention
gate fails. There is no default change, favorable-subset replacement, larger
campaign or unchanged rerun. The incomplete construction prevents a broad
method ranking; even the feasible subset is descriptive rather than a new gate.

Candidate queries are legacy113/32,206nodes/5.401s versus semantic159/
43,033nodes/7.661s. Those totals include different trajectories and are **not**
a same-work evaluator slowdown estimate. Every one of11 first trajectory
divergences occurs at the candidate;5 pairs stay identical. Nine first
divergences have equal completed depths, two do not.

A posthoc component diagnostic uses those11 exposed states, with no new games.
All132 D1 queries complete. Core/Native agree on500 child attack maps and all
component action/score pairs, with identical511 total nodes per authority and
component. Static-only authority choices all match; coverage-only and anchor-only
choices each differ on8/11 states, both on10/11. Thus actual evaluation semantics
matter even at equal depth. This does not turn differing actions into useful play.
The both-term D1 query totals are legacy0.0981s, Core0.2071s, Native0.1009s;
single short measurements on exposed states do not establish a stable speed ratio.

## Recomposition validity is a joint condition

The same eight frozen substrates were subsequently compiled in a geometry x
capture-condition factorial, with no games or setup repair. Orthogonal clear
capture compiles for8/8; orthogonal one-screen capture for4/8. Six original
types have ray controls: all six clear and all six screen variants compile.
The other two types have no original ray and those control cells stay unsupported.
For the six complete factorials, two fail only the joint change. The other two
failures do not have complete original-ray controls. Do not claim a complete
four-case causal interaction proof or turn the four valid rules into full-domain
coverage. Initial-state validation must follow the actual composed rule.

## Cheap method selection and sampler feasibility

[Clune2007](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf), pp1136–1137, uses
fixed-role feature stability together with rule dependencies and separate payoff,
control and termination models. It does not propose ranking arbitrary side-to-move
engine scores by stability alone. Reusing the24 complete calibration histories
gives804 ongoing states: all six rules exhibit component-order reversals when
the fixed-role frame is replaced by side-to-move, and ply count has the largest
fixed-role quotient in all six. This rejects a raw stability-only selector here,
not the paper's complete method. No weights are fitted or learning started.

[Soemers et al.2021](https://arxiv.org/html/2111.02839v1), sections5/7,
specializes random sampling under explicit legality and distribution conditions.
Its reported throughput gains are not imported as GenericChess evidence.
The current mining policy has category selection with empty-category fallbacks,
which requires a separate derivation. Running that actual chooser with controlled
classification oracles and120 exactly weighted tapes gives a counterexample:
one quiet legal move, one legal drop and one illegal pseudo-capture change the
drop probability from4/5 to13/17 if legality is repaired by blanket rejection.
This is an algorithm-level witness, not an illegal Core position or a current bug.

For the **uniform legacy-only** case, a private feasibility prototype deduplicates
public pseudo Actions, shuffles uniformly and returns the first legal member.
It explicitly refuses semantic rules. Reusing21 ongoing6/8/10-board roots gives
126 validated choice calls; all six rule medians improve83.5–94.2% in choice-only
cost. A uniform permutation gives each unique legal member equal first-accepted
probability. Omitting deduplication would bias6/21 roots, with maximum total
variation21/170 from the intended uniform distribution. The observed actual
choice timings are microbenchmarks, not whole-game or acquisition speedups.

The complete random-turn follow-up includes public checked `Session.submit`:
126 one-ply transitions, all full successors replayed and parents unchanged.
Per-rule median reductions are33.5–43.6%, but five rules save only0.244–0.568ms;
one saves2.357ms. Only1/6 meets the registered joint20%/1ms gate, which requires
four rules. **Defer implementation**, despite the attractive choice-only ratios.
All63 paired draws choose different actions, so this is not an isolated
same-action execution-cost contrast. Common clone/replay, initial generation and
AlphaBeta turns are excluded: no whole-acquisition or whole-game speedup follows.

There is no new API/default or mutation of frozen opening RNG tapes. Reconsider
only with a real consumer dominated by this cost. The category sampler is a different policy;
semantic, promotion/drop variants, auxiliary state and history cannot be dropped
to generalize the legacy prototype.

An earlier pre-cancelled fallback screen on these21 roots measured252 calls:
per-rule public medians0.6–3.6ms, no rule met its5ms optimization gate. Requested
Native mode made zero provider calls because these are legacy rules; this is
not a Native/Core semantic comparison. First-legal choice differs on11 roots
and does not itself satisfy the full terminal/declaration caller contract.
No cancellation optimization or stress campaign follows.

## Verification and reproducibility limits

The executed programs and literal outputs are retained, including failed slots,
all actual game records, count observations and posthoc selections. Programs
expect repository-root cwd and the test semantic fixtures. Copy the data directory
to an ignored private working directory before execution: producers write their
outputs beside themselves and must not overwrite the retained actual evidence.
Timing-dependent
queries can differ on a rerun; the retained records are the actual evidence.
The first utility producer aborted before games on the initial invalid setup;
its corrected producer records validation failures instead of aborting or refilling.
No frozen played outcome was discarded. Production clock source was unchanged
during that closed trial; subsequent LF normalization changed no Python semantics.

Full active regression initially yielded3,478 passes,74 build-fixture errors
and two temporary-Git-test failures. The build errors identify inaccessible
Python link libraries; local Git transport was also sandbox restricted. Normal
escalation reran the four affected files:93 pass, covering all76 unsuccessful
cases and17 overlapping passes. No expected value or test contract was weakened.
The remaining pytest-cache access warning does not change test outcomes.
