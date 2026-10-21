# Reusable fixed-scale episode TDLeaf

Current research direction changed by direct user instruction2026-10-21 to
finite Leaper foundations and conditional value/learning mechanisms. This file
retains the learner and historical results, not an instruction to expand old
strength/lambda/opponent panels. See LEAPER_DIRECTION.md and
LEAPER_FOUNDATION_20261021.md. The last opponent panel is STOPPED_USER with
32missing slots retained; prepared old successors are deferred, not resumed.

`generic_chess.learning.incremental` contains the opt-in Model, bounded
material-blind AlphaBeta, episode-frozen TDLeaf(.95), Chess and full GameSession
adapters, and one shared training/evaluation episode loop. It has no runtime
imports from experiments or proof scripts and changes no product defaults.
The existing `learning.tdleaf` batch implementation remains separate.

Current Generic episodes default to `learning.mainline_search`,a thin receipt
adapter over sandbox's public iterative q0 AlphaBetaPlayer. The randomized
AlphaBeta below is retained for Chess and explicit `search_backend='reference'`
historical controls. It is not another evolving Generic rules/search baseline.
Historical commands below refer to their fixed source revisions; on the current
runner select `--search-backend reference` when inspecting those old policies.
Never overwrite/restart their closed output directories.

Current adapter source00e39117 also enables the existing mainline TT and move
orderer within each query. Capture-order values are identically zero; TT moves,
captures/promotions and killer/history stages introduce no piece-price prior.
Players are fresh for every query, preventing cached scores from another model
or a deeper earlier request from becoming shallow training targets. Literal
q0 PV/model agreement, actual terminal verification and all paid partial work
checks remain mandatory. No shared search implementation or product default is
changed. Historical TT-off reports below retain their original policies.

Fixed coordinate 0 stays 1, scale 10, eta .05, lambda .95. Search weights are frozen
within each episode. Targets use player-0 perspective, including when the
candidate plays player 1. UNKNOWN retains observed interior search transitions
but supplies no final draw target. Generic qsearch is rejected; all Generic
queries use qdepth0. Owned declarations, including LOSS, remain real choices;
RESTART/NO_CONTEST never become draws. Incomplete queries pay visited nodes,
produce no root action/training receipt and leave the full session unchanged.

### Optional last-completed-depth decisions

`completed_depth_search` reuses the same q0 AlphaBeta at D1 through a requested
depth. Attempts share one node allowance and deadline; all shallow searches and
failed deeper searches are charged. Action, PV, samples and TD target come only
from the last complete depth, recorded as `completed_depth`; `attempted_depth`
and the compact attempt costs distinguish it from a completed deeper search.
An incomplete first depth has no action or label. External cancellation,
episode/global time limits and a non-scoring terminal reject fallback. The
episode checks its guard again before observation or committing the action.
Local query exhaustion can retain a complete shallow result; reaching the
episode node cap then ends before starting another decision. There is no
continuation of a previously capped game and no change to fixed-depth defaults.

The episode API accepts explicit opponent depth/iteration settings so a
candidate-search comparison can keep its foe fixed. Both sides still pay into
the same game cap. Equal maximum budgets do not mean equal realized work or
isolate a pure depth effect: deeper work may consume the allowance earlier.
Full W/L/D/UNKNOWN completion bounds remain necessary.

One fresh natural-rule feasibility episode (generator seed2026102101, search
seed27184, uniform weights, D1→D2,8192/query,40000/game,H64,120s) made57 plies
in61.748s and ended NODE_CAP_UNKNOWN. It paid4122 D1 nodes,31418 complete-D2
nodes and4460 partial-D2 nodes.55 decisions completed D2; two retained D1.
The two fallback actions/PVs independently match D1 searches at the same
history and seed.23 captures,13 drops and one promotion were replayed through
GameSession.29 learner observations yielded28 interior TD errors; the final
UNKNOWN supplied no outcome target. An independent forward-lambda reconstruction
matched the weight update exactly. This establishes executable fallback and
learning arithmetic on this trajectory, not stronger play. The prior capped
episode remains closed. Raw evidence stays under ignored artifacts/.

Of those28 TD errors,25 are D2→D2, two D2→D1 errors happen to be zero, and
one D1→D2 error contributes.008062875 of.064611126 total half-squared error.
Its eligibility-weighted update partly cancels other updates; target-depth
changes cannot be inferred from the final coefficients alone. Variable-depth
search targets are the specified approximation, with no convergence or fixed-D2
claim. This diagnosis does not justify filtering targets after seeing outcomes.

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

In the preceding segment, one previously unsampled default `GeneratorConfig(seed=2026102101)` game,
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
No retry or independent holdout/playing-strength claim followed that episode.
The next question was a last-completed-depth target/choice
contract at this preserved root before proposing further natural-input work;
an incomplete D2 must never be relabeled as an exact D2 target or a draw.
One separately budgeted D1 query at that preserved late root completes64
nodes in.062 seconds, with value-4 and a nonterminal leaf. No action is
committed and the old episode remains UNKNOWN. Combining this completed D1
with the earlier failed D2 is only a design example, not an executed iterative
search: a real policy must pay both searches under one decision budget and
record the depth actually supplying its training target. This is the next
specific interface question; that segment launched no further training panel.

## Fixed-foe depth control, 2026-10-21

Source `bc43cf6717076c4662547a6c675c733fc146839f`. The same exposed natural rule
uses eight new unselected random-opening paths, seed27185, both candidate colors,
and uniform1 weights everywhere. Candidate modes are fixedD1 and iterativeD2;
the foe remains fixedD1. Shared per-game maxima are8192/query,60000 nodes,
90s,H128; total maxima are1.2M nodes/1800s. Mode order alternates by family;
paired modes use identical starts and search seeds. No training takes place.

All32 slots finish in546.307s with311936 search nodes,1362 queries and no
missing slots. All histories and actual outcomes independently replay:
27 checkmates,5 ongoing UNKNOWN. FixedD1 gives6W6L4UNKNOWN; iterativeD2
gives13W2L1UNKNOWN. Over16 color-paired comparisons the full completion bound
for iterative-minus-fixed payoff is **[3/8,1]**. This bounds the UNKNOWN
outcomes on these eight correlated families, not a confidence interval or a
claim about a rule population. Three families have definite mean gain1,
two have exact0, and three have unresolved nonnegative ranges.

Realized cost is122464 nodes/216.406 game seconds for fixedD1 versus189472
nodes/327.119s for iterative. Candidate-only nodes are61232 versus174422;
foe nodes are61232 versus15050 because actual trajectories differ. Iterative
attempts include31135 paid incomplete nodes. Equal allowances therefore do
not establish benefit per equal realized node or isolate fallback itself.
The control supports retaining iterative play for the next learning check on
this rule; it does not establish a gain from learning, general strength, or
convergence to human piece prices.

The next single-rule learning test was specified before its launch: seed27186,
random uniform[.5,1.5] nonfixed weights, fixed board-P1, same uniform D1 foe,
iterativeD2 candidate,128 training episodes max,16 evaluation families×2 colors
×2 profiles,2M nodes per phase,3600s overall with training in the first1800s,
H128,60000/game and8192/query. The 10–40s typical games plus occasional longer
histories in the control justify a bounded one-hour ceiling. A single trajectory
cannot answer the learning-strength question; the preceding control cannot
substitute for trained-versus-initial play. This exposed-rule study retains
all UNKNOWN/missing slots and receives no topup. Positive completion bounds
would support a later fresh-rule check; an unresolved result leaves weights
unadopted and motivates using saved mechanisms rather than enlarging this panel.

The natural input is reproducible from the existing generator rather than a
new experiment framework: `generate_game(GeneratorConfig(seed=2026102101,
max_generation_attempts=32)).ruleset`, serialized with `ruleset_to_dict` to
`artifacts/natural-rule-20261021.json`. Other generator settings are defaults.
The learning entry and complete configuration are:

```powershell
.venv\Scripts\python.exe -m scripts.incremental_learning --rules artifacts/natural-rule-20261021.json --unit P --seed 27186 --train-episodes 128 --eval-pairs 16 --train-nodes 2000000 --eval-nodes 2000000 --seconds 3600 --horizon 128 --depth 2 --iterative --opponent-depth 1 --no-opponent-iterative --query-nodes 8192 --game-nodes 60000 --output artifacts/natural-iterative-learning-20261021
```

These describe the executed study, not permission to overwrite or rerun its
closed outputs. Timing-dependent fallback need not reproduce identical paths
under another machine load. Raw traces remain ignored; the public code,
generator configuration and finite results supply the compact research record.

### Completed learning result

Producer exit0, PLANNED_EPISODES_COMPLETE:3569.873826s overall. Training phase
measured1800.061268s against its intended1800s guard; the.061s atomic/final
bookkeeping overrun is retained. The guard stayed1800s; strict real-time
compliance is not established.

| Measure | Result |
|---|---|
| Training | 70 episodes,65 nonzero updates;1109513 search nodes |
| Training outcomes | 63W,5L,2UNKNOWN:68 actual checkmates,one H128 cutoff,one TRAIN_TIME_CAP |
| Evaluation | 64/64 slots;62 actual checkmates,2 node-cap UNKNOWN,0 missing;1021306 nodes |
| Trained candidate | 29W,1L,2UNKNOWN |
| Initial candidate | 28W,4L,0UNKNOWN |
| Full paired reward bound | **[1/16,3/16] = [.0625,.1875]** |

The known reward-difference sum is4; the two unknown payoffs give `(4±2)/32`.
This is identified finite gain on the16 exposed root families under this fixed
uniform D1 foe and resource recipe. It is not a sampling CI, an independent
rule/position holdout, general strength or amateur-level calibration. No weights
were made a default. All original caps and all incomplete results remain closed.

All134 recorded histories/results and3841 query records were checked against
their node totals. All70 training updates independently reconstruct within
4.44e-16; evaluation profiles remain exactly frozen. There are878 material
target errors,61 terminal-PV target errors and65 actual-final errors. Two actual
final updates have nonzero terminal credit; early zero final errors did not
make the actual terminal term universally redundant.929 nonzero-gradient
nonterminal feature rows span all9 nonfixed coordinates. Feature span is not
parameter identifiability or proof of convergence. Three training games and
two evaluation games ended before the candidate made a search query; they
remain in the complete result, rather than being selected away.

Channels are `board(P,A,B,C,X), hand(A,B,C,P,X)`. Frozen final weights:
`[1,2.279657581919599,.7073754491890226,.8848782315545707,1.4560110105137922,2.831721226867124,1.013947638639077,.4406555938954061,-.787552454077756,1.2329929442245295]`.
This includes a negative hand-P approximation; it is neither clamped to a human
prior nor asserted to be a universal marginal value.

One outcome-selected illustration, index4/color0, first diverges at new ply3.
Both queries complete D2 on the same history/seed,1455 versus1565 nodes;
trained moves(2,3)→(3,5), initial moves(7,0)→(4,6), with zero-based coordinates.
The actual games end trained win44plies versus initial loss33plies. This rules
out an incomplete-depth explanation at that particular first divergence, not
ties, later resource effects, or every alternative cause of the final outcome.
No coefficient ablation, new search or gameplay was performed for this diagnosis.

Evaluation candidate work totals91645 complete-D1,688348 complete-D2 and166807
partial-D2 nodes, plus74506 foe nodes. Failed D2 attempts consume331.917 of
1766.121 episode seconds; complete D2 consumes1162.270s. Thus complete deeper
search, not just failed work, dominates this measured cost. These are local
elapsed costs under ordinary concurrency, not portable throughput claims.

The next useful step has begun with one label-blind prospective default sample:
generator seed2026102102, max32 structural-filter attempts, accepted on attempt3,
56 opening actions. One uniform-price D1→D2 root query completes443 total nodes
in.527s with no committed action. It establishes initial feasibility only;
the previous late-query failure shows why an initial root cannot establish
episode throughput. Next run one fresh bounded episode with the same learner,
not transferred learned weights, before choosing another training run. Stronger
foe calibration remains a separate future question; no MCTS/Elo framework follows.

## Reuse committed mainline infrastructure, 2026-10-21

Direct user correction makes published sandbox infrastructure the default
sidemission baseline. Imported source is sandbox
`6a4f8868d767b41ffc07ff5ddbb7bce448417aaa`, including Core no-progress context,
history identity/terminal precedence, rule execution, Python/Native search,
evaluation and their product/development/specification tests. Native rebuilt
locally. DEV_AUX's episode learner and role-local records remain independent;
no PRIMARY uncommitted work, results/producers or operational state is adopted.

The learner now creates the shared Core SearchPathRuntime for hypothetical
search children. Full root admission, including no-progress replay, is paid
inside the existing query time allowance. Actual episode moves and saved
records remain GameSession operations. `use_runtime=False` selects the public
session reference for validation; it implements no separate rules or adjudicator.
Material channels now read typed semantic support without requiring an
inspection-only legacy handle. No TD arithmetic, material priors, q0 admission,
last-completed-depth rule, UNKNOWN handling or frozen old results were changed.

One bounded local D2 comparison uses identical seed67183, unit weights,
100000nodes/30s per query and all paid root work. On two actual8-ply no-progress
histories, reference/runtime agree exactly on17/23nodes, action, value, PV
features/terminal flag and every interval sample. Public transition replay calls
fall150→8 and210→8; the8 calls are the once-per-query root admission. In one
measurement elapsed time is.0586→.00724s and.0770→.00694s. On the second natural
rule at its real ply8 history, both complete552nodes with identical results;
elapsed time1.039→.215s (about531→2564nodes/s). These are single local timing
observations under ordinary concurrency, not portable speedup estimates or
playing-strength effects. Search-node visits are not primitive transition counts.

All238 shared package source files match the fixed sandbox commit after normal
Git line-ending normalization; `learning/incremental.py` is the only AUX-only
package file. Final integration regression:3953passed,1skipped in325.35s.
The first attempt's3 failures and74 errors remain private: two retained proof
prototype tests encountered stricter root admission, one temporary local Git
transport test lacked sandbox permission, and Native fault-build fixtures lacked
access to the existing Zig library. The optional prototype now explicitly uses
its public legal fallback when Core rejects incomplete adjudication history;
Core admission is unchanged. The permitted rerun fixes the test environment;
no checks were removed or skipped to obtain the passing result.

The second natural rule's original fresh feasibility episode (before enabling
the shared search path) used seed27187, random[.5,1.5] nonfixed coordinates,
uniform fixedD1 foe, iterativeD2 candidate,H64,8192/query,60000/game and120s.
It ends actual player0 checkmate after11plies/11queries/6686nodes in10.775836s.
All history replays and one nonzero frozen-episode TD update complete; terminal
credit is0 because its final search prediction is already terminal. This is one
feasibility episode, not strength, transfer of weights or evidence of a second
rule's learning gain. Its old cap/output is closed.

Next use the previously frozen first-rule trained and initial weights in direct
iterativeD2 games with paired colors/openings and a small fixedD3-foe calibration.
The old D1-foe study stays unchanged. Different studies' bounds[3/8,1] and
[1/16,3/16] cannot establish a causal ranking of depth versus learning gains.

### Direct same-depth play and max-D3 calibration

Source4a1d459a9445b0649d2d94941734464259492d25. Frozen first-rule trained and
initial vectors above play directly, both using iterativeD2/q0. Eight prospective
random-opening families fromseed27188 are used with both candidate colors;
none of their starts equals a start in the old134recorded episodes. This is
not independent rule holdout. A second arm uses initial iterativeD2 against
uniform iterativeD3 on the first4families/both colors. MaxD3 is a configured
ceiling, not a guarantee that D3 completes. Both arms haveH128,8192/query,
60000nodes/90s pergame; declared overall maxima1.44Mnodes/1800s. No training,
reselection, resampling or closed-run continuation occurs.

All24slots finish,0missing,987027nodes/208.432s. Direct trained-versus-initial
gives **4W9L3UNKNOWN**,507027nodes/114.626episode seconds. The trained mean
payoff's finite completion bound is **[-1/2,-1/8]** and its score lies[1/4,7/16];
all three unknowns are node-cap/ongoing. These are completion bounds, not CIs.
Thus this16game condition disfavors the trained vector even under favorable
completion of all unknowns. It does not refute the old D1-foe result or prove a
population ranking; opponent/search conditions and opening families differ.
The committed Core baseline also changed; this is not an isolated intervention
on the old experiment's opponent.
No learned weights are adopted.

The8calibration games all reach60000nodes and remain UNKNOWN (480000nodes,
92.389episode seconds). Initial candidate queries complete71D2; foe queries
complete34D3,38D2fallback and3D1fallback. The foe spends260417nodes on partialD3
attempts versus105456on completedD3. Consequently this recipe supplies neither
a fixed-complete-D3 opponent nor a50percent strength anchor. No extra allowance
or topup follows. All24full histories/results and777query records independently
replay/check, including both colors, frozen vectors and every paid attempt.

Next is separate second-rule learning against a uniform iterativeD2 foe,
freshseed27189/random initialization,128planned training episodes/16evaluation
families (64slots),2Mnodes perphase,1800s overall/900s training,H128,
8192/query/60000game. This tests the same algorithm on another previously
selected rule under stronger opposition. Changing both rule and opponent
does not isolate an opponent-strength treatment effect. No first-rule weights,
old episode continuation, old cap reset or new infrastructure framework.

### Second natural rule, uniform D2 foe

That separate seed27189 run is closed at source4a1d459a. Training reaches the
original2Mnode cap after80episodes/77nonzero updates (128was a ceiling),
562.852phase seconds; no topup. Evaluation completes64slots with56actual mates,
8node-capUNKNOWN and0missing,1476496nodes. Total elapsed972.514826s. Trained
gives **8W19L5UNKNOWN** versus initial **23W6L3UNKNOWN**; paired known difference
is-28 with8unknowns over32pairs, giving **[-9/8,-5/8]**. This finite condition
rejects improvement, not all TDLeaf methods or the rule domain. No weight adoption.
All144histories/4588queries and80updates check independently within2.22e-16.
There are1149material,63terminal-PV and63actual-final error terms. Feature
gradients span9nonfixed coordinates; that does not imply learnability or gain.

The initial vector still wins23of32 against uniform D2, so depth alone does
not guarantee a balanced opponent. The failure cannot be repaired by filling
UNKNOWN, choosing a favorable checkpoint or extending the closed cap.

One prospective check now selects classic TDLeaflambda1 on this same rule with
freshseed27190:eta.05/scale10 unchanged,uniform iterativeD2 foe,H128,
8192/query/60000game,128training ceiling/64evaluation slots,2Mnodes perphase,
900s training/1800s overall. The hypothesis is that anchoring completed episodes
to their actual return can help when early bootstrap predictions are poor,
following the paper's section4.2 suggestion. Censored episodes still omit the
final reward and use only observed search transitions. This is one fixed
alternative,not a hyperparameter scan. New initialization/openings mean it tests
gain versus its own initial vector,not a causal lambda1-versus-.95 winner.
No priors,variant target filtering or additional rule panel is introduced.

### Literature and signal interpretation

Baxter, Tridgell and Weaver's [KnightCap paper](https://arxiv.org/pdf/cs/9901002)
(sections3–4) permits varying completed search depth and describes opponent
diversity as important. Its successful run starts with conventional material
values; a uniform-initialization run learns more slowly. It also filters some
positive temporal errors caused by unpredicted opponent moves. These conditions
differ from this material-only, random-initialized vanilla learner, so its rating
results are not a strength promise or permission to add priors/blunder filtering.
Keep the selected algorithm; test its actual outcomes under the declared foe.

Own saved first-rule data further qualify "almost no terminal learning signal":
the final actual-outcome error is usually zero, but61transitions target a
rule-terminal PV. For hand-P, aggregate observed update contributions are
material-.71847,terminal-PV-1.27809,actual-final+.23973, summing to-1.75683.
This arithmetic attributes updates on the observed trajectory, not the cause of
direct-play losses or a counterfactual training effect. Changing targets would
also change later weights/actions, so an offline sum cannot stand in for a new
training/strength test. No labels, weights or completed-run results were changed.

## Rule2 lambda1 check and fresh depth-cost control

Source288c8dc88f35c06ba2bc9b0956d21e016655afa9. The one prospective lambda1
check ends PLANNED_EPISODES_COMPLETE in931.656892s. Training stops at the
original2Mnode limit:75episodes/74nonzero updates,542.755616phase seconds.
There are64actual-terminal training episodes and11censored episodes; no missing
final reward is fabricated. Evaluation completes64slots/0missing,55actual mates
and9node-capUNKNOWN,1335023nodes. Frozen trained gives **20W10L2UNKNOWN**;
initial gives **9W16L7UNKNOWN**. Known reward difference17 plus/minus9unknowns
over32pairs gives **[1/4,13/16]**. This is finite own-initial gain in this
condition,not a CI,population claim or lambda-method winner. The prior.95run's
different initialization/openings prevent causal attribution to lambda.

All139full histories/4425query records and75TD updates independently check
within2.22e-16. A separate lambda1 telescoping calculation uses
`eta * sum(gradient_i * (return - prediction_i))`: actual return for completed
episodes,last observed search prediction for censored interior transitions,
with no final UNKNOWN label. It agrees to2.22e-16 over1298observed candidate
roots. No learned vector is selected as a default.

The shared entry reproduces this declared recipe (closed outputs must not be
overwritten or continued):

```powershell
.venv\Scripts\python.exe -m scripts.incremental_learning --rules artifacts/natural-rule-2026102102.json --unit P --seed 27190 --td-lambda 1 --train-episodes 128 --eval-pairs 16 --train-nodes 2000000 --eval-nodes 2000000 --seconds 1800 --horizon 128 --depth 2 --iterative --opponent-depth 2 --opponent-iterative --query-nodes 8192 --game-nodes 60000 --output artifacts/natural-second-lambda1-learning-20261021
```

Both saved natural rules still regenerate identically using the current shared
generator atseeds2026102101/2026102102 withmax_generation_attempts32 and other
defaults. Latest published sandboxd2da9705bb7993e41d7920aad4439e5156059ede has
research-only changes since6a4f886; all238shared package files still match.
Its existing custody/ordering and finite-goal results were read at that fixed
revision. Reuse their distinctions; no duplicate price-region,PV-rank or
history-alias audit was launched. Actual learner ordering is material-independent.

### New resource condition,not a refill

One separate predeclared control uses rule2,seed27191,two fresh opening families,
both candidate colors,unit1weights everywhere and a fixed uniform iterativeD2foe.
Candidate ceilings are iterativeD2 anditerativeD3. Both have16384/query,
240000nodes/90s pergame,H128; overall maxima1.92Mnodes/900s,eight slots.
Mode order alternates by family; starts/search seeds are paired. There is no
training. These are new histories and a new allowance,not continuations or
relabels of the old rule1/60000node maxD3 calibration games.

All8slots complete in150.920461s,731055nodes,0missing. D2 gives2W2L;
maxD3 gives2W2node-capUNKNOWN. The finite maxD3-minus-D2 bound is **[0,1]**;
this does not identify strict benefit. D2's two color games in each family have
identical full paths and opposite payoffs,as expected for identical players.
All8histories/251query records independently replay/check. D2 uses55864nodes/
20.724episode seconds; maxD3 uses675191nodes/129.716seconds. Different paths
and realized work prevent a per-node speedup or equal-compute interpretation.

MaxD3 candidate queries complete39D3 and20D2fallbacks,spending311553nodes on
completedD3 and290919on partialD3. The foe has57D2/1D1query in those games.
Both capped games retain240000nodeUNKNOWN. No additional budget or sample is
added. Neither this control nor the earlier[3/8,1]depth result can rank search
versus learning effects across different rules/roots/opponents.

### Next useful comparison

The two rule2 runs show opposite gains under different initializations. Before
choosing lambda,cost one coupled comparison with a common new seed/initial vector
and common new evaluation starts. A useful design has two equal training arms
(2Mnodes/900s each),then three frozen profiles including ONE shared initial
control over16families/both colors. Give each profile1Mnodes/400s rather than
letting a late profile consume only leftovers:7Mnodes/3000s maximum overall,
96planned evaluation slots. Observed costs suggest roughly30process minutes,
plus about15minutes of engineering/audit; below the120minute assessment threshold.
This is a prospective cost/design step,not a registered or executed study.

Compare each trained profile against the common initial,and compare the two
trained profiles' paired fixed-foe payoffs. This is not a head-to-head matchup.
In the lambda contrast `(R1-Rinitial)-(R95-Rinitial)=R1-R95`,the shared initial
outcome cancels,including its UNKNOWN uncertainty; do not count it twice by
subtracting independently widened gain intervals. Each own-initial contrast
still retains every unknown/missing payoff. Per-profile time allowances must
charge that profile's opening/play/replay work,not wall waiting during another
profile. Preserve resource differences. One coupled seed can distinguish this condition,not prove
initialization robustness or population superiority. No hyperparameter grid,
favorable-checkpoint selection,new framework or repeated old fitness follows.

### Coupled comparison,prospective 2026-10-21

Use fresh seed27192 on the same exposed natural rule2. Both arms start from the
same random[.5,1.5] vector with fixed unit1,receive the same ordered random-opening
and search seeds,and use the unchanged library learner atlambda.95/1. Each arm
has128episode ceiling,2Mnodes/900s. The fixed foe is uniform iterativeD2; candidate
is iterativeD2,H128,8192/query,60000/game. Then freeze both vectors and evaluate
16new opening families/both colors against that foe,with ONE shared initial
profile:96slots. Each profile gets1Mnodes/400s of its own opening/play/replay time,
not elapsed time during other profiles; the overall fuse is3000s/7Mnodes.
Node/time exhaustion retains UNKNOWN/missing slots,no extension or replacement.
This compares entire bounded learning policies: the two training trajectories
can diverge and reach different numbers of episodes under equal allowances.

The existing entry now has optional `--compare-lambda`,per-arm `--train-seconds`
and per-profile `--eval-seconds`. The legacy single-arm defaults remain. A real
six-slot q0 smoke completes with no missing slots; all6outcomes are horizonUNKNOWN.
50focused tests pass,including shared initialization/root/search seeds,independent
profile budgets and fixed missing-slot denominators. No engine/rules fork added.

```powershell
.venv\Scripts\python.exe -m scripts.incremental_learning --rules artifacts/natural-rule-2026102102.json --unit P --seed 27192 --td-lambda .95 --compare-lambda 1 --train-episodes 128 --eval-pairs 16 --train-nodes 2000000 --eval-nodes 1000000 --train-seconds 900 --eval-seconds 400 --seconds 3000 --horizon 128 --depth 2 --iterative --opponent-depth 2 --opponent-iterative --query-nodes 8192 --game-nodes 60000 --output artifacts/coupled-lambda-20261021
```

### Public mainline search reuse,prospective follow-up

The three natural q0 caller checks preserve fractional scores and match their
literal GameSession PV material and the old full-depth reference value. Their
work differs with lexical versus randomized traversal; no speed/strength gain is
claimed. Configuredq1hard1 only retainedD1/q0 in this probe. Mainline qsearch
returns scalar values without its continuation in the public PV,so no q1 TDLeaf
feature is inferred or separate qsearch written.

A thin `learning.mainline_search` adapter calls the existing public
`AlphaBetaPlayer`,disabling TT,price ordering,root tactical scans and optional
pruning. Mainline rules/history,search,default legality-provider policy and
terminal distance preferences remain; this does not claim optional Native
availability/check probes ran. Full GameSession PV replay supplies player0features. It
rejects incomplete/fallback,nonliteral,neutral-declaration and non-scoring
targets rather than manufacturing a draw. The old randomized learner search
will remain an explicit historical reference,not the default Generic caller.
14real boundary regressions pass,including float values,partial-node payment,
stop-after-search,actual no-progress draw,full-history repetition,winning
declarations for both players,and rejection of neutral/altered-score targets.

PV extraction copies the already authoritative full session before submitting
the line; it does not replay the played prefix on every query. On one saved
95ply ongoing history,five copies took0.000659s versus0.540640s for five full
prefix replays,state/record/search-witnesses equal. This measures that operation
only,not end-to-end search acceleration. Episode-end and independent full-record
replay remain. No played history is discarded by the optimization.

After the coupled producer closes,wire this existing public q0 caller into
future Generic episodes and obtain ONE bounded actual learning/play pilot.
This question is infrastructure/learner execution,not a favorable lambda rerun
or public-versus-reference strength ranking. Fix lambda1 and fresh seed27193
now,before coupled fitness:rule2,128train ceiling,2Mnodes/900s train;
16families/both colors/trained versus initial,2Mnodes eval,1800s total.
Both players use public iterativeD2,q0,H128,8192/query,60000/game. Preserve all
UNKNOWN/missing. Reuse the same model/update/episode loop; no new engine or
generated tracked output. Neither this pilot nor the coupled comparison selects
deployed weights or claims robustness across initialization or rule families.

### Coupled result,closed

Sourcee4c8c193821fa7d7223abd2d42c6c3adb0df1df5 exits0 in1715.759183s,
6492852nodes. Each training arm consumes exactly2Mnodes:lambda.95 has65episodes/
63updates/45actual terminals/20UNKNOWN,lambda1 has64/63/47/17. Training phase
times512.397796/541.425312s; the64common opening histories and the first
11query/complete-game trajectory match before their first different update.

All96evaluation slots finish,79actual mates/17UNKNOWN/0missing. Lambda.95 gives
10W14L8UNKNOWN,lambda1 gives24W5L3UNKNOWN,shared initial gives11W15L6UNKNOWN.
Own-initial bounds are[-7/16,7/16]and[7/16,1]; the direct method contrast is
**[3/8,17/16]**,with the one shared baseline cancelled exactly. This is a
strict finite-condition lambda1 advantage,not a population CI or robustness
claim. Each profile stays below1Mnodes/400s; realized eval costs are972926/
542630/977296nodes and247.608/156.970/257.276s. Equal maxima are not equal work.

All225full histories,7657queries and129TD updates independently check:
max backward-sum error2.22e-16,independent forward-target error1.39e-16.
For actual terminal returnz,the lambda-weighted TD error for observationi is
`-v_i +(1-lambda)*sum_{k=i+1}^{T-1} lambda^(k-i-1)*v_k +lambda^(T-i-1)*z`.
Atlambda1 this telescopes toz-v_i. Censored sequences end with the last
observed search prediction and no final reward. These are arithmetic checks,
not claims that coefficient changes identify intrinsic piece prices.

Future Generic entry wiring has98focused boundary/episode/history regressions
passing. Four historical seed/path/node assertions explicitly select their
original reference backend; their old results are not rewritten as mainline
runs. A real public-caller smoke retains missing/node-cap slots at its small
budget. The preselected seed27193pilot still uses the unchanged TD update.

### Prospective frozen direct control

Before the public pilot's fitness is known,select one direct trained-versus-own
initial control,fresh opening seed27194,32families/both colors/64slots. Both sides
use the same public iterativeD2,q0,H128,8192/query,60000nodes/90s per game;
total maxima3.84Mnodes/900s. Freeze the completed pilot's final checkpoint without
selection or further training. All zero-query terminal starts,UNKNOWN and missing
remain. This can distinguish fixed-uniform-foe gain from actual direct matchup
payoff; it is not Elo or a cross-rule claim. Expected5-12minutes,below120minutes;
16families would be cheaper but halve the distinct opening conditions. No
closed source,roots,budgets or evaluation slots are resumed or topped up.

### Public-mainline pilot,closed without evaluation topup

Source0ac747671bf692a9174c526f712ab9a9cd642dc6,seed27193,exits0 with
EVALUATION_CAP in687.302251s. The same TDLeaflambda1 update and episode loop
actually call public mainline iterativeD2q0 for both players. Train2Mnodes,
354.205583s,57episodes/54nonzero updates:35actual terminals and22UNKNOWN
(21game-node caps,one unfinished first-layer legal fallback). Two random
training starts were already terminal; three episodes contain no candidate
query. These remain in the declared sample,not evidence of successful learning.

Eval reaches its original2Mnode limit after46of64planned slots,not the time
limit:23actual mates,23UNKNOWN,18missing. Trained=6W4L13UNKNOWN/9missing;
initial=5W8L10UNKNOWN/9missing. The full32-pair bound is **[-9/8,23/16]**,
so utility is unresolved. No games/slots are resumed,filled or reclassified.
All103full histories,2481query records and57TD updates independently check
within2.22e-16; incomplete/fallback queries have no numeric training label.

This establishes the public-search learner's actual execution,not strength
or a portable acceleration claim. Its different fresh seed,lexical traversal,
mate-distance preferences and realized histories prevent causal speed/strength
comparisons with the reference-backed studies. Public q0 literal-PV/float
contracts hold on the observed accepted receipts. Actual played moves remain
authoritative GameSession operations; no Core/search/qsearch source was forked.

After both completed producers exited,the full product/development/workflow/
specification suite passed **3969tests,1skipped,in330.39s**. It used an own
artifact temp directory and existing read-only dependencies; no other role's
checkout/state was changed. The subsequent direct matchup is a separate
predeclared cohort,not completion of the pilot's18missing evaluation slots.

### Frozen public direct control,closed

Seed27194,32new opening families/both colors:all64slots complete,0missing,
460.422458s/2919897nodes. Frozen trained versus its own frozen initial gives
**16W5L43UNKNOWN**,mean trained-payoff bound **[-1/2,27/32]**. This is a direct
matchup payoff,not a trained-minus-initial fixed-foe gain. It establishes no
strict benefit. All21scoring results are actual mates;42games hit their60000
node cap and one has no completed first-layer result. No zero-ply starts,
training,checkpoint selection,refill or UNKNOWN adjudication occurred.

All64full histories and1157queries independently replay/check,including
candidate/foe vector identity,player0scores,literal-PV values and paid partial
work. Queries complete1065D2/91D1fallbacks/one unfinished first layer. Thus this
condition is mainly game-node-censored rather than universally unable to
completeD2. No inference of general superiority or product-weight adoption.

Next cost question:reuse the existing public TT/full-PV support with separate
fixed-model players inside each episode,clearing between model updates. The
current adapter deliberately starts fresh with TT off. Read existing warm-PV/
history/reset contracts first,then compare a few saved same-state queries under
equal caps; verify score/PV/model epoch before claiming a completion benefit.
Do not write another TT/search implementation. A newD3panel or lambda seed
replication is less useful while this finite evaluation remains mostly capped;
neither is permanently barred or a reason to extend closed experiments.

### Closing mainline delta

The final explicit fetch found sandboxbffe1e4b5f0a98ca6215eae3b83b329962db37db.
Its238shared package files still match; only the two AUX learner modules differ.
The common research_record GameRecord serializer fix is reused verbatim,with
its five new regressions. The actual promotion/drop/aux fixture is bound to
already shared test data locally,avoiding restoration of PRIMARY's price-region
experiment drivers just for a fixture import. All80record/learner tests pass.
The earlier3969/1skip whole-suite result remains explicitly the pre-helper run;
no full-suite rerun or new experiment was necessary for this isolated helper fix.
Our actual learner records already used the strict public serializer; frozen
inputs/results and their actual source revisions are unchanged.

PRIMARY's fixed new Native-service/hybrid-alias report was read. Adopt actual
consumer timing versus paid/ordered work,full physical-history alignment,and
the difference between additional completed depth and utility. Same seeds do
not guarantee matched histories across representations. Do not copy its current
q1probe task or infer our Native speed/q-tail support. Existing warm-TT tests
also retain deeper cached scores on shallower requests until reset: the next
learner TT check must validate actual PV/value provenance and model epochs.

### Existing ordering and TT reuse, 2026-10-21

Four saved complete-history roots (first four families of the closed27194
direct cohort, frozen trained vector) were chosen before new queries. The
24-call TT probe used coldD2, repeatedD2 and then warmD1, TTon/off,8192nodes/
1.8seconds each,48seconds overall. It completed in0.980s. ColdD2nodes were
389/318/212/250 with either TT setting; repeatedD2 withTT used2nodes per root.
All corresponding D2scores and literal leaves matched. However,three of four
warmD1calls retained a deeper cached score while exporting a one-ply line whose
raw material value differed. On the fourth,the accidental scalar match still
does not establish shallow minimax provenance. The public deeper-cache behavior
is documented; legal sufficient-length PV is weaker than literal TDLeaf target
provenance. The learner keeps fresh per-query players, rather than enabling
persistent caches or modifying the shared search to impose another contract.

A separate16-call factorial compared coldTTon/off and existing orderingon/off
atmaxD3,16384nodes/2.8s each,48s overall. Capture priorities were equalzero;
the existing orderer supplied TT/capture/promotion/killer/history stages. It
completed in18.597s. No-order completedD3atthree roots;order completed allfour.
On the three jointly completed roots,values were unchanged and nodes fell
8389→1797,8061→1119,9953→3736 withTT+order. The fourth moved from cappedD2/
16384nodes to completeD3/6824nodes,which is a completion comparison,not equal
realized work. TTalone left these cold query counts unchanged. These finite
same-state measurements support reusing existing ordering,not a general speed,
strength,Native throughput or changed-policy game comparison claim. Tied leaf
features may differ when ordering changes. No tree walk,TT or orderer was added.

Source00e39117 enables fresh per-query TT and the existing equal-capture-price
orderer in the AUX receipt adapter only.82learner/runtime regressions pass,
including allfour TT/order combinations at fullD3 and sequential model/depth
changes. Existing cancellation,history,no-progress,declaration,UNKNOWN and
aborted-node accounting remain tested. The earlier full-suite result is not a
new whole-suite execution for this change.

One new prospective seed panel is frozen under ignored
`artifacts/ordered-seed-panel-20261021/config.json`:train seeds27195/27196/27197,
public orderedD2q0,lambda.95,eta.05,random independent initial vectors,uniform
publicD2training foe. Each seed gets atmost512episodes/5Mnodes/800s; frozen
trained then plays its own initial on64common opening families/both colors,
atmost4Mnodes/600s per seed. H128,8192/query,60000nodes/90s per game; whole
experiment27Mnodes/4200s (70min,below120min assessment threshold). No seed,
checkpoint,training-length or result-based selection/topup. All128planned
evaluation slots per seed remain in the denominator,including missing/UNKNOWN.
This measures combined initialization/training-opening dispersion on one exposed
rule,not population confidence,lambda superiority or a causal speed comparison
with older un-ordered trajectories. No weight adoption follows.

Claude's seed-variance advice is adopted with this qualification. Primary
sources [Henderson et al.](https://arxiv.org/abs/1709.06560),section Random Seeds
and Trials,and [Colas et al.](https://arxiv.org/abs/1806.08295),sections1/5,
support reporting seed variation and avoiding selected best runs. They do not
provide a universal sufficient seed count; their empirical deep-RL findings
are not measurements of this linear TDLeaf learner. Three seeds here are a
bounded exploratory dispersion check,not a powered superiority test. Missing/
UNKNOWN completion intervals answer unresolved finite outcomes; they are not
sampling confidence intervals. Common evaluation roots improve comparability
but do not turn the384planned games into384independent training replicates.

The panel closed atGLOBAL_TIME_CAP,exit0,4200.124380s/8983167nodes. Its exact
executed source is00e391172f63c7f6259a9e91d1d4f2060be5a3e8 (sharedbffe).
Training completed106/113/102episodes,with98/109/100changed updates;305actual
terminals/16UNKNOWN overall. Every seed stopped at its original800s allowance.
Opening/replay/control time is paid;episode-only time is not the phase total.

| Seed | Direct W | L | D | UNKNOWN | Missing of128 | Mean payoff completion bound |
|---|---:|---:|---:|---:|---:|---|
|27195|39|46|0|4|39|[-25/64,9/32]|
|27196|93|16|0|7|12|[29/64,3/4]|
|27197|69|28|1|5|25|[11/128,71/128]|

All384planned slots remain in the pooled denominator:201W90L1D16UNKNOWN and
76missing give[19/384,203/384]. This establishes positive pooled payoff for
these finite three training conditions,not a population confidence interval.
Seed1and2intervals are separated by11/64 even under adversarial unresolved
outcomes;their difference is combined initialization/training-root/resource
variation,not an isolated initialization coefficient effect. No model or seed
is chosen as a product default. No lambda-method comparison was performed.

Independent replay/arithmetic checked629full histories,26353queries and321TD
update calculations;maximum forward-weight error1.33e-15. All14526train and
11819evalD2queries are paid. Two eval queries retainD1 at a local node limit;
six other queries report one completed layer but reject the target on a live
phase/global stop (three train,three eval). Node/phase/global limits and
unconsumed final queries are preserved. The original summary has only two seed
entries because the final global guard exits before appending the third. Its
103durable final-seed evaluation rows and frozen weights independently yield
the last row above;the original summary is preserved,not patched or rerun.
These are actual search-node counters;wall time also includes legality,history,
PV checks,serialization and control. Different played histories preclude a
causal speed comparison with old policies.

### Latest committed infrastructure and fresh-rule reuse

After that frozen producer exited,the final fetch found sandbox
6ea35571272708f7e220fa3868f2ca1a4d0cf7ca. Its three AlphaBeta files,maintained
semantic_probe_cost interface and two regression files are reused exactly;
all238shared package files match.167affected learner/search/history tests pass.
Read PRIMARY's Q_HORIZON_POLICY_AND_EARLY_WIN report atthat revision:more
completed depth is not outcome utility;any-completed-root-win is neither a
uniform-depth nor literal-PV promise. The new option remains defaultfalse in
the learner. Q1still lacks an exported q continuation for TDLeaf features.
PRIMARY's experiments/tasks were not adopted or rerun.

The preselected fresh generator seed2026102103 succeeds on its first attempt
(maximum32,otherwise default8x8classic_like config). Under exactsource
b83eaab13124491006a69a2c3b2848014c858568,the SAME publicD2q0 learner plays one
episode (27199,60000nodes/120s/H128,8192/query,uniform foe). It closes after
85legal plies/85queries/20149nodes/8.430631s with an actual player0win,18drops
and4promotions.43candidate observations produce a nonzero TD update;independent
series reconstruction has error0 and the full record replays. Final terminal
credit is0 because the last search already predicts that terminal;do not
misattribute all learning to the final W/L signal. There is no rule reselection,
held-out strength claim,old-cap reset or new game-specific search.
