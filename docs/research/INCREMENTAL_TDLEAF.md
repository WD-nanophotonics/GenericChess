# Reusable fixed-scale episode TDLeaf

`generic_chess.learning.incremental` contains the opt-in Model, bounded
material-blind AlphaBeta, episode-frozen TDLeaf(.95), Chess and full GameSession
adapters, and one shared training/evaluation episode loop. It has no runtime
imports from experiments or proof scripts and changes no product defaults.
The existing `learning.tdleaf` batch implementation remains separate.

Fixed coordinate 0 stays 1, scale 10, eta .05, lambda .95. Search weights are frozen
within each episode. Targets use player-0 perspective, including when the
candidate plays player 1. UNKNOWN retains observed interior search transitions
but supplies no final draw target. Generic qsearch is rejected; all Generic
queries use qdepth0. Owned declarations, including LOSS, remain real choices;
RESTART/NO_CONTEST never become draws. Incomplete queries pay visited nodes,
produce no root action/training receipt and leave the full session unchanged.

The initial extraction's twenty-four regression cases independently check the forward lambda sum,
real Chess mate learning, full promotion/drop/auxiliary/history replay, all
declaration outcomes, cancellation, terminal-on-last-ply, and budget censorship.
Twenty-three retained learner/adapter regressions also pass. A transient legacy
comparison matched 60 real search receipts and 20 complete episode updates exactly
apart from elapsed time; old pinned source files were not modified.

## One-rule semantic exploration, 2026-10-21

Decision question: does this common path obtain nonzero TD updates and actual
terminal play evidence when promotion, base-hand drops and temporary auxiliary
state coexist, or does the chosen distribution supply no useful learning signal?
This is algorithm reuse on one rule, not cross-rule knowledge transfer, an
independent holdout, general strength, or a claim about amateur play.

Input: `data/incremental_semantic_pilot_20261021.json`, a balanced-material
six-actor 8x8 stress rule derived from existing semantic fixtures. Two R per
player can capture to hand and drop under a zone guard; a semantic diagonal
move changes R to TP and creates an expiring global right. That right is carried
through the real game even though this fixture has no action conditioned on it.
Movement/geometry can be asymmetric; evaluation balances candidate color.

Configuration: seed 8173; declared board-R unit; remaining coordinates initially
uniform[.5,1.5], with no human material prior. Uniform-weight opponent; D2/q0,
8192 nodes/query, 100000 nodes/game, H128. At most 128 training episodes and 32
evaluation root families x 2 colors x 2 profiles. Both learned and initial profiles
use the same per-game resources, roots and search-order seeds. Family profile
order alternates. Fresh random opening paths have 2–8 moves; these fixture-based
paths are exploratory, not independently withheld positions or rule families.

Cap: 1M combined candidate/foe training nodes, 1M evaluation nodes, 1800 seconds
overall, with training restricted to the first 900 seconds. Missing slots and
UNKNOWN remain explicit. The root D2 calibration visited 94 nodes in .091s;
full replay, opening construction and branch variation add cost. Projected
all-in execution stays below the fixed 30-minute deadline and 120-minute consultation
threshold. No result-driven extension or top-up is permitted.

The 20-second lifecycle smoke completed 2 training episodes and 4 evaluation slots
in 9.502s / 9207 nodes; all four evaluation games were UNKNOWN and no update
occurred. Those H16 smoke outcomes do not establish learnability or strength.
The longer exploratory run uses H128 as specified above and remains a separate
new study, not a retry of any frozen experiment.

Reproduction (run from this checkout; raw traces stay ignored):

```powershell
.venv\Scripts\python.exe -m scripts.incremental_learning --rules docs/research/data/incremental_semantic_pilot_20261021.json --unit R --seed 8173 --train-episodes 128 --eval-pairs 32 --train-nodes 1000000 --eval-nodes 1000000 --seconds 1800 --horizon 128 --depth 2 --query-nodes 8192 --game-nodes 100000 --output artifacts/incremental-semantic-pilot-20261021
```

The compact results follow; raw traces remain ignored. The reported completion
bound treats unknown or missing payoffs as possible [-1,1]; it is not a confidence
interval. A nonzero update, changed action, or predictive score is not W/L/D.

## Result

Executed source: `b82f8fd562d44aaaa7df8eb38b39338f07bb1dc0`.
The controller exited normally with `GLOBAL_TIME_CAP` after **1800.026 seconds**;
this is a budget-limited experiment, not completion of all evaluation slots.
No retry, top-up, seed change, longer horizon or extra worker followed.

| Quantity | Observed |
|---|---|
| Training | 119 episodes, 821001 nodes, 106 nonzero updates |
| Training outcomes | 88 actual terminal, 30 horizon UNKNOWN, 1 resource-limited UNKNOWN |
| Final weights: board-R, board-TP, hand-R, hand-TP | 1, -1.4936545341993783, 0.8918021874503936, 0.9971011348572694 |
| Evaluation | 95 of 128 slots; 839294 nodes |
| Evaluation outcomes | 52 actual terminal, 43 UNKNOWN, 33 missing |
| Trained profile (candidate-oriented) | 15 W, 0 D, 6 L, 26 UNKNOWN; 17 missing |
| Initial profile (candidate-oriented) | 22 W, 3 D, 6 L, 17 UNKNOWN; 16 missing |
| Full planned paired reward-difference completion bound | **[-83/64, 69/64] = [-1.296875, 1.078125]** |

The initial weights were `[1, 0.5805624412612915, 0.5585141092367637,
0.9971011348572694]`. Training used an intended 900-second phase bound,
before the 1M-node cap or 128-episode maximum; it was not deliberately extended
to use the unspent node allowance. Later source review found that the original
runner computed remaining episode time before constructing its opening and
checked only the overall deadline inside search. The precise training-phase
endpoint was not logged, so strict 900-second compliance is **not established**.
The measured 1800.026-second overall exit and all saved results remain unchanged.
One incomplete query in each phase retains its nodes
and supplies no action/label. Independent summation of query costs agrees
with the episode totals: 1660295 nodes overall.

The exact bound uses 64 planned root/color pairs. Known payoff-difference sum
is -7; the 43 unknown plus 33 missing individual payoffs allow an uncertainty
of +/-76, hence (-7 +/-76)/64. This makes no confidence or population claim,
and does not treat unknown games as draws. Raw terminal-only rates compare
different selected subsets and are not a valid estimate of improvement.

Zero-search paired-path analysis found 47 pairs with both profiles closed:
24 identical action paths, 23 with an actual action divergence. Every first
divergence was on the candidate's turn, consistent with changing only its
prices. All 18 pairs with two actual terminals had equal reward; 29 closed
pairs contain UNKNOWN. One additional pair has only the initial profile,
and 16 pairs are entirely missing. This demonstrates some policy response,
but neither benefit nor equivalence/non-inferiority. No observed evaluation
start history exactly matched a training start history, but only 24 of the
32 evaluation families were reached; this fixture-based exploration is still
not an independent withheld rule/position distribution.

**Decision:** keep the reusable implementation; do not adopt these weights,
claim Generic strength, or extend the same panel. The useful next investigation
is one mechanism explaining why the 23 action-changing pairs provide no
identified terminal gain, with any resulting hypothesis explicitly post hoc.
Only a decision-changing mechanism warrants a new bounded study; it would
need genuinely separate validation rather than relabeling these exposed roots.
Raw query/episode/config/summary files remain ignored under
`artifacts/incremental-semantic-pilot-20261021/`.

## Mechanism and interpretation

This fixture has an exact unidentifiable direction: hand-TP. Initially every
base type is K or R. Ordinary movement/capture/drop preserves those base types;
the only type-changing semantic effect sets CURRENT type TP, and the only
placement effect uses an existing hand's base type. Inductively no base-TP
piece or hand holding is reachable from these starts. Thus hand-TP features
and gradients are zero, and changing that coefficient cannot change the
material evaluation or price-independent search order on this support.
Its failure to move is not learner failure, a unique correct price, or a
reason to remove the channel from arbitrary other rules.

For the first 42 completed training episodes, independent forward-sum
reconstruction of 1547 learner observations agreed with saved weights within
1.25e-16. Signed TP update: interior search transitions -0.635950761,
final actual-outcome error +0.005174419. Corresponding hand-R contributions:
+0.123586388 and -0.000547424. Only one episode had a nonzero last-target
contribution. These are a declared training-prefix mechanism diagnosis,
not a checkpoint selected for evaluation. Terminal PV predictions can already
inject a rule-terminal search signal into an interior transition; "interior"
does not mean all these targets were nonterminal material estimates.

Negative learned TP weights remain unconstrained observations of this
approximation. They do not establish that adding a TP has negative causal
value: a legal piece-addition counterfactual, location, history and other
pieces would have to be specified. Nor does an active gradient prove that
the chosen action changes or that any action change improves W/L/D.

Rule execution covers the real typed actions and history, while the material
representation remains approximate. In particular, a search branch reaching
RESTART/NO_CONTEST conservatively makes the root query incomplete, retaining
its visited-node cost and producing no action/target. This is not a complete
playing policy for every rule and does not certify a fallback player.

Measurement environment: Python 3.12.14, Windows 11 x86-64, 20 logical CPUs;
single CPU search process, no GPU. Ordinary regression tests overlapped the
initial run interval. Node conditions are fixed; this is not a CPU-isolated
timing comparison and no throughput/strength portability is claimed.

## Post-hoc decision mechanism, next continuation

Full-history replay of the 23 divergent pairs explains a concrete response,
without supplying their unknown outcomes. The first divergence in pair1
(family0, candidate player1) occurs at relative ply127. Both branches have
material features `(0,1,-1,0)`. Initial chooses K `(1,3)->(0,4)` and the real
session declares repetition draw. Trained chooses `(1,3)->(0,3)` and remains
ongoing at H128. Its nonterminal D2 value is `t-h=-2.38545672`, below the actual
draw's zero in player0 coordinates, so minimizing player1 prefers continuation.
This is observable draw avoidance, not evidence that continuation wins or loses.
Initial had a terminal PV; trained did not.

Pair3 (family1, candidate player1) supplies a small complete decision tree.
Its first divergence is relative ply29, after 33 actual history actions, with
features `(-2,2,0,0)`. An independent D2 enumeration visited **213 nodes**:
30 root choices and 182 nonterminal leaves. Set `t=board-TP`, `h=hand-R`, with
board-R fixed at1; hand-TP is unreachable here. Player1 minimizes these exact
root-action values:

| Root choices | Count | D2 value | Condition for being optimal |
|---|---:|---|---|
| Capture group, including K `(7,7)->(7,6)` | 3 | `B=-2+t-h` | `t+h>=0` and `h>=-1` |
| Retain group, including R `(7,0)->(3,0)` | 22 | `A=-2+2t` | `t+h<=0` and `t<=1` |
| Third leaf group | 1 | `C=-1+t` | `t>=1` and `h<=-1` |
| Two-reply-feature group | 4 | `max(A,D)`, `D=-1+2t+h` | ties A only when A is optimal and `h<=-1` |

These are regions of equal **complete-tree optimal action sets**, not a claim
that the randomized alpha-beta implementation selects the same tied action
throughout a region. Its cutoffs consume the random ordering stream differently
when prices change. These conditions follow from `A-B=t+h`, `C-A=1-t`, `C-B=1+h`, and
`D-A=1+h`; they retain ties. Exact rational evaluation at 1089 grid points
(`t,h=-4..4` by1/4) agreed with the conditions. This checks a derivation for
this one tree, within the evaluator's finite magnitude limits, not a universal
piece-value law. At `(t,h)=(1,-1)` all30 actions tie. Along the segment between
the saved initial and trained weights, the only optimal-group change is at
interpolation coefficient **0.65429240235**, where `t+h=0` and25 actions tie.
Initial has three optimal capture actions; trained has22 optimal retain
actions, with no intersection. Their exact values match the frozen query logs.
The saved training trajectory first crosses `t+h<0` after episode93 and remains
there for its last26 episodes; no checkpoint was selected or adopted.

A separately bounded diagnostic used D3 and D4, each profile limited to16384
nodes/20seconds per query. All four searches completed, using7800 nodes in
total, and retained the same initial capture / trained non-capture choices.
None had a terminal PV. This is a depth response on an exposed root, not an
additional game, independent validation, or a continuation of censored games.
The initial saved game eventually wins for player1; trained remains UNKNOWN.
Consequently the action's causal W/L/D effect is still unidentified.
The subsequent fixed D8 probe allowed400000 nodes/480 seconds per profile.
Both hit their original node caps, after373.237/381.268 seconds. All800000
nodes are paid; neither returned an action, value or training label. This
does not establish D8 preference persistence or a W/L/D result, and was not
retried with a larger cap.

Reconstruction of **all119 training episodes /4319 learner observations**
agrees with saved per-episode weights within1.12e-16. Decomposing the *TD error
endpoints*, while retaining the full eligibility trace, gives:

| Error category | Terms | Signed TP update | Signed hand-R update |
|---|---:|---:|---:|
| Material prediction -> material prediction | 4120 | -0.581358599 | -0.011179193 |
| Material prediction -> rule-terminal search PV | 82 | -1.498032795 | +0.345014696 |
| Last prediction -> actual played outcome | 86 | +0.005174419 | -0.000547424 |

Two actual-terminal starts supply no learner observation, hence86 final terms
for88 actual-terminal training episodes. Approximately72.22% of the net TP
fall comes from errors targeting terminal PVs. Thus “almost no final-outcome
residual” does not establish absent terminal supervision or explain the
negative weight by itself. These contributions describe this realized training
path, not effects of removing any signal and retraining.

As a countercheck against equating negative coefficients with failure, the
chronologically first saved positive task2625 pair
`(271001,1977,4000047,color0)` has initial loss and TDLeaf win, both actual
checkmates after24/31 evaluation plies. Their first actions differ; the learned
hand-P weight is negative (`-0.1504368753`). Both final records were replayed
from the historical rule at `7fe1a9d6e3ab2772e520afc0784627ebd7e7d9c4`.
This is an outcome-selected illustration, not a new validation sample or proof
that its first action alone caused the gain. It gives no reason to constrain
coefficient signs or fit to human prices.

Additional actual-rule regressions retain the conservative semantic boundary:
an eight-action continuous-check history trains the actual player0 loss with
the analytically correct negative update; a genuine no-progress draw stays
distinct from an external horizon; and WIN plus RESTART/NO_CONTEST still makes
the root query incomplete even though a real winning declaration exists.
This remains an AlphaBeta-query limitation. The shared player now checks Core's
available declarations first and commits a currently authoritative WIN before
starting search. It never values the neutral option or invents a search receipt.
Only the actually executed declaration supplies the terminal target. Without
an available WIN, non-scoring alternatives retain the conservative UNKNOWN path.
Assessment/commit time is included in the episode deadline; query/node counters
count search work. Stop, time and exhausted-node guards still prevent actions.
For a scoring-only old path, omitting a zero-gradient terminal-PV observation
immediately followed by the same actual outcome preserves the TD update: the
earlier error is unchanged and the omitted final error was zero.
A real capture-to-hand, opponent move, then WIN-with-neutral-control episode
checks the analytic nonzero hand-R update and exact history replay. Alternate
initial setups, pass draws and both candidate colors also have regression
coverage. The final focused/related command passes59 cases.

The runner now subtracts opening/replay time before granting episode time,
checks the training deadline during opening and search, and records measured
training-phase elapsed time. Two controlled-clock regressions reproduce the
old stale-budget window. Timing checks cannot preempt an individual atomic
operation or final durable logging; they stop further work at the next guard.
No old experiment is rerun or granted a larger budget by this fix.

Raw diagnostic trees/decompositions remain ignored under `artifacts/`; the
published equations and semantic regressions are the compact evidence summary.
This work supports mechanism understanding and budget correctness, not weight
adoption, generality, strength, or an Elo/amateur-level claim.

## Prospective no-progress rule pilot

This separate exploratory game changes only the original input's no-progress
policy:32 consecutive non-capture plies automatically draw; captures reset it,
with no mover-type reset. Original movement/promotion/drop/auxiliary rules,
fourfold repetition and max-ply512 stay unchanged. It does not retroactively
adjudicate any old UNKNOWN. Fresh seed27182 initializes
`[1,1.1748229339,1.1402175549,.7860686783]`; the common learner and uniform foe,
D2/q0,8192/query,100000/game,H128 remain as before. Maxima are128 training
episodes and32 evaluation families x2 colors x2 profiles,750k search nodes per
phase,1200 seconds overall with the first600 reserved for training. Raw input
and traces stay under ignored `artifacts/`.

Executed source: `b2d3846dfa0e64dd354eb833e17b2a7d1dce9398`, before the later
WIN-declaration shortcut. This input has no declarations. The process exited0
at `GLOBAL_TIME_CAP`,1200.022907 seconds; measured training phase600.151721
seconds. These small guard/atomic-operation overruns are reported, not described
as strict deadline compliance or used to authorize more work.

| Quantity | Observed |
|---|---|
| Training | 48 episodes/48 updates;166488 search nodes |
| Training endings | 17 checkmates,9 actual no-progress draws,22 resource UNKNOWN |
| Final weights | `[1,1.1850034975,1.2878917855,.7860686783]` |
| Evaluation | 46/128 slots;143089 search nodes;82 missing |
| Evaluation endings | 18 checkmates,12 actual no-progress draws,16 resource UNKNOWN |
| Trained candidate | 2W,6D,6L,9UNKNOWN,41missing |
| Initial candidate | 2W,6D,8L,7UNKNOWN,41missing |
| Full planned completion bound | **[-3/2,25/16] = [-1.5,1.5625]** |

All94 final histories replay; query/episode totals agree at309577 search nodes.
All48 TD updates reconstruct exactly in the separate summation. There are507
material-target errors,26 terminal-PV-target errors and26 zero last-outcome
errors. TP contributions are -.05282538 from material targets and +.06300594
from terminal-PV targets; hand-R contributions are +.01085047 and +.13682376.
No final draw was supplied to any resource-censored episode.
Known reward-difference sum is2;16 unknown plus82 missing payoffs leave98
unknown quantities, giving `(2 +/-98)/64`. The bound is not a CI or evidence
of gain/equivalence. Changed seed, rule and budget prevent a causal comparison
with the first pilot. These remain unselected random-opening paths on an
exposed stress fixture, not independent natural-rule validation.

The current no-progress checker reconstructs authoritative complete history
after the ply threshold. A separate common-history D1 control at absolute
ply32/quiet-count24 gives the same6 search nodes, choice, score and leaf features
under the base and no-progress inputs. Internal `apply_action` calls rise from5
to170: five real successors each replay33 actions. Instrumented times are
.0051/.4278 seconds, with ordinary concurrent work; these are not portable
throughput claims. Search-node counts omit that internal replay work; elapsed
time charges it. Thus adding a correct adjudication rule is not by itself a
cheap cure for censoring on this implementation. No history check was bypassed,
Core/PRIMARY code changed, old cap reset or weight adopted.

## Next natural-input feasibility

One previously unsampled default `GeneratorConfig(seed=2026102101)` game,
with max32 existing structural-filter attempts, succeeds on attempt1:8x8,
32 actors,40 opening legal actions and10 board/hand channels. One uniform-price
D2/q0 query completes311 nodes in.258 seconds with nonzero PV features despite
zero symmetric root counts. This establishes limited input/cost feasibility.

One separately bounded episode uses uniform initialization/foe, the unchanged
TDLeaf rule, candidate0,D2,H64,8192/query,20000 game nodes,60 seconds,seed27183.
It stops at a query resource limit after16 actual plies/17 queries,12438 nodes
and17.457 seconds, retaining UNKNOWN. Eight valid learner observations give
seven interior errors and a nonzero update; there is no terminal label.
Full history replay and node sums match. The failed last query consumes2360
nodes and supplies no action/value. The final root has63 legal choices
(26 board,37 drop), versus40 initially, and both players have hand holdings.
This identifies a late-query resource problem, not its sole causal mechanism.
No second episode, retry, validation panel, independent holdout or playing
strength claim follows. Next examine a last-completed-depth target/choice
contract at this preserved root before proposing further natural-input work;
an incomplete D2 must never be relabeled as an exact D2 target or a draw.
One separately budgeted D1 query at that preserved late root completes64
nodes in.062 seconds, with value-4 and a nonterminal leaf. No action is
committed and the old episode remains UNKNOWN. Combining this completed D1
with the earlier failed D2 is only a design example, not an executed iterative
search: a real policy must pay both searches under one decision budget and
record the depth actually supplying its training target. This is the next
specific interface question; no new training panel has been launched.
