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

Twenty-four new regression cases independently check the forward lambda sum,
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
0.9971011348572694]`. Training stopped at its original 900-second phase bound,
before the 1M-node cap or 128-episode maximum; it was not extended to use the
unspent node allowance. One incomplete query in each phase retains its nodes
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
