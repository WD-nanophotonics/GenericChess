# Pure-Leaper clock horizon, q ordering and exact depth ceiling

## Current result

The actual p53 error remains open. Completing more clock-frontier q moves did
not improve it: the last-ply prototype was slower with the same wrong D7 action;
full <=4-ply completion regressed the equal-budget late-history panel from
16/16 to15/16 correct. Neither prototype is activated.

A different, conservative optimization is implemented in the backend as an
**opt-in, default-false** `AlphaBetaPlayer(cap_pure_leaper_rule_clock=True)`.
For admitted hard-clock pure Leapers it caps requested main depth at remaining
rule plies. Ten candidate queries preserve every shared complete iteration's
action, score, main/q work and root value against ten already-paid controls.
Eight short-clock DRAW roots finish in13.353s rather than87.906s, with85520
rather than307059 work events. Two larger controls remain budget-limited.
This is a scoped latency result; it neither repairs p53 nor establishes strength
or success across the pure-Leaper class. No UI/default, evaluator, q policy,
Core transition/history/clock, TT identity/guard or node/time cap was changed.

## Scope, goals and registration

All producers are closed. The existing180minute recurrence and AUX boundaries
are untouched. No new worker, solver/graph, training, Elo/human-label fit,
NNUE, mixed-rule optimization or old-cap refill was used.

| Phase | Actual successful Player returns | Scope/goal | Result |
|---|---:|---|---|
| Return observer |0, with1 failed attempt|One45s p53 read-only trace|D1–5 exact prefix preserved; D6/7 trace UNKNOWN|
| q-order prospective cost |32|8 exact rules,16 complete histories,120s each arm|11 nontrivial pairs preserve all shared scores;5 immediate-win pairs have no common depth|
| Existing-PV clock endpoint |1|Actual ply60 endpoint,remaining4,Q0/fullD4|0 terminal-only value vs static−1106|
| Last-clock-ply ablation |6|p7,p49,p53;matchedD7/45s|No repair; p53 slower despite actual activation|
| Full-clock completion feasibility |2|p53,same any-win goal,1Mwork/240s|Neither arm obtains reported mate-band win before node cap|
| Full-clock completion move quality |32|All16 existing histories withremaining<=16;20s/250k each|Default16/16;candidate15/16;only regressionp53|
| Backend hard-clock ceiling |10|All10 existing histories withremaining<=10;reuse paid controls|Exact common prefixes;8 complete,2 limited|

Total:83 successful returns,1 failed attempt,551 legal exported PV steps.
PV legality is not551 independent complete proofs. Reused controls are counted
once. Each phase has a different explicit goal; fixed-depth parity, first correct
action, reported mate-band return and final timed decision are kept separate.

The q-cost registration fixed mask pairs(5,7),(6,9),(7,12),(9,17),(10,19),
(11,20),(12,23),(13,24),4x4 six-actor starts,clock64/repetition4, and initial/p5
histories before queries. P5 comes from seed20261025 legal random walks with
nonterminal preparation, not candidate outcomes. Both seats are represented;
initial/p5 actor and history effects are confounded. These are prospective cost
strata after prior q results, not an independent WDL holdout. Immediate wins were
retained, not replaced by harder favorable cases.

The labelled phases use one exposed5x5 four-actor RuleSet and complete histories
from the fixed published AUX26d414cce26d44e7d2cfae84a20195fa715f2906 input.
Core replay binds rule/state/actor/frontier and every exported action. This is
published label reuse and shared Core, not independent solving. Full rules and
histories are never truncated. Candidate results do not choose labels/order.

The completion20s panel was formally registered after the first proof-feasibility
candidate result was observed. It is **post-pilot exposed falsification**, not
blind-to-pilot validation. All16 late histories were then frozen, with no cherry
selection, extra masks, threshold grid, rerun or timeout enlargement.

## What the failed observer does and does not show

The one observation attempt failed after1.902s because generic dataclass recording
of `RuntimeSearchState` recursively reached its `SearchPathRuntime` owner. The
receipt's queries=0 counts saved returns, not attempts; the separate accounting
records1 attempted call,0 completed returns. Original source/exception remain
private; the public exception is a path-sanitized copy. D1–5 match the paid
control's action, score and main/q counts exactly. Unpersisted D6/7 child windows
and q-return aggregates are lost and remain UNKNOWN. No new run filled that slot.

The maintained future recorder projects runtime position/ply/result/history
explicitly, saves partial traces on failure, and distinguishes setup from actual
call attempts. Three zero-Player-query regression tests pass; the repaired full
observer has not been executed. The failed executed-source capsule remains exact.

## q ordering: measured cost, no nontrivial WDL claim

All11 nontrivial pairs preserve every common completed root score. At their
highest shared depth the median work ratio is0.834833 and time ratio0.853499.
Work ratios range0.754702–0.995611; measured time ratios0.739288–1.009323.
The0.9percent slower observation is small and uncontrolled-load sensitive: it is
not statistical evidence of a true slowdown, but measured speed is not uniformly
better. Histories within each rule are related; no confidence interval treats
16 histories as independent rules. Full depth/cost curves are published.

The5 immediate-win pairs have actual one-ply Core wins verified but0 common
main iterations; they provide no deep-q cost/parity evidence. Other WDL quality
is UNKNOWN. Actual Native legality calls=4812199,operational failures=0. This
covers those calls, not all provider states. All runtime stacks restore.
RequestedD64 was not a completed-depth success on the22 time-limited returns.

## Finite-clock utility and the two rejected policies

The p53 D7 exported main PV ends atply60,remaining4,ongoing,static−1106.
One existing-search Q0 query completesD4 withscore0/204 total nodes; cumulative
evaluation calls are40 at bothD3 andD4. Thus its final layer uses terminal values,
not static leaves. This qualifies that endpoint's finite-clock value through the
existing search/Core contract, not an independent all-domain proof and not the
actual missing q-return/root-window trace.

Last-ply completion changes only noncheck/no-neutral q nodes at remaining1,
searching all legal actual terminal children. Declaration/terminal/check paths,
hard/q-node/cancellation controls and fresh-policy TT separation are retained.
P7 andp49 never activate and preserve exact common prefixes. P53 enters10720
times and searches148743 terminal children, yet D7 remains1106/DRAW;29.414s
becomes39.111s. This is an observed negative, not absence of execution.

Full <=4 completion admits only q nodes with enough original hard8 depth room,
then follows all legal children to authoritative Core terminals. Pending or
nonterminal-at-clock behavior is never relabelled DRAW. Under the same any-win
goal and1Mwork/240s per arm, the candidate uses1M events in120.427s, completesD6
and choosesDRAW; control uses1M in148.623s, completesD9 and also choosesDRAW.
Neither produces a reported mate-band winning return. The candidate is cheaper
per counted event but uses its work budget less usefully. Control's first correct
complete action isD6 at11.704s; candidate has no correct completed iteration.
This is not a default45s match or a universal proof-cost comparison.

The separate equal20s/250k move panel returns16/16 correct for default and15/16
for completion, no repairs and onlyp53 regressing. Atp53 the control retainsD6
WIN while candidate retainsD5 DRAW. Local terminal correctness does not guarantee
better root decisions under a shared resource cap. Do not activate either q
prototype, globally extend q, fit prices or increase caps to erase these results.

## Backend option: stop after a genuinely complete hard-clock horizon

The default caller sometimes continues toD31/D64 after already completing the
entire remaining rule clock. In the admitted scope, full main depthH reaches
actual Core terminals on every surviving path: every move advances the clock;
no admitted policy can leave play pending beyondmax_ply. Iterations deeper thanH
cannot add a longer playable continuation. Capping requested depth atH retains
all earlier search and its q semantics. It does not select a historically good
D6 when p53 actually has11 plies remaining.

Admission conservatively excludes automatic/pending and other extra adjudication
policies, declarations, aux/triggers, non-draw repetition, active hands/drop
masks/capture-to-hand, legacy promotion masks and non-Leaper executable geometry. Metadata and
semantic clock must agree. The complete record stays intact. Unsupported rules
keep their original limit. A shallower/zero explicit request remains unchanged;
None retains the engine's64 default before applying a genuine smaller bound.

All10 real-data shared prefixes match exactly. The8 completed cases have H1–8
andDRAW labels; eight cost totals87.906s→13.353s and307059→85520 visits/events.
The H10/H9 controls still time out below their ceiling and do not claim completion.
Elapsed measurements have concurrent-load limits; removed complete-prefix work
is directly counted. Engineering/test/record/delivery overhead is not amortized
by these8queries; no net project-wide total-cost saving is claimed. The backend option defaults false and is not wired into UI.
`last_rule_clock_cap` reports a requested ceiling, never a proof of completion.
Live cancellation and all other SearchLimits fields remain authoritative. No TT
key/cache-policy change is needed because q/evaluation semantics are unchanged.

## Next useful work already begun

The new saved control gives a scalar-alias witness: score1103 corresponds to a
known WIN action atD6 and a DRAW action atD8 at the SAME full root. Neither score
nor odd/even depth can safely choose an earlier action. This offline join was
started without another Player call and is published as the next witness.

Keep the difficult quiet-winning branch/time-to-correct question as Main. Ask
Dot which cheap observable can discriminate quiet-threat support from root
allocation before another tree change. Do not replay the failed observer slot,
use Oracle ordering/price thresholds, or keep sweeping masks/timeouts. Hard-clock
ceiling generalization and safe first-return q reserve remain subordinate.

## Validation and delivery

51 unique relevant tests pass (repeated publication gates are not extra unique
tests). An invalid initial-in-check unit fixture and a missing Rider drop mask
were diagnosed at compiler validation and corrected with their expectations
unchanged. A default system pytest temporary-directory denial was handled with
pytest's supported fresh ignored basetemp; no ACL/security changes were made.
8 UTC-zero short calls are individually retained in the raw scientific data;
the final accounting reports their uncredited status. Nonzero perf_counter cost is
retained scientifically, but zero-length UTC spans are never credited to work.
A42.824ms overlapping analysis start was rejected and conservatively moved to the
next second; the rejected attempt added no time or duplicate intervals.

Exact active-session acceptance and work intervals are in the accompanying
accounting copy. Raw originals remain ignored. Decoded outgoing archives/source
were reviewed for personal paths and credentials; source bytes are tied to their
frozen hashes. Capsules are data and must never be executed. Public readers and
exact input/source provenance are in the [packet README](data/leaper_clock_horizon_20261025/README.md).

Accepted session: 21399c2a-600c-46b3-9c1a-8bd936b434b3; UTC 2026-10-24T21:14:07.514031+00:00 to 2026-10-24T22:49:01.985689+00:00; 4195.6984059999995 effective seconds/77 intervals. finish/final-check PASS. Administrative delivery after finish adds0 research time.
