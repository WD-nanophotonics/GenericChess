# Reusable fixed-scale episode TDLeaf

`generic_chess.learning.incremental` contains the opt-in Model, bounded
material-blind AlphaBeta, episode-frozen TDLeaf(.95), Chess and full GameSession
adapters, and one shared training/evaluation episode loop. It has no runtime
imports from experiments or proof scripts and changes no product defaults.
The existing `learning.tdleaf` batch implementation remains separate.

Fixed coordinate0 stays1, scale10, eta.05, lambda.95. Search weights are frozen
within each episode. Targets use player0 perspective, including when the
candidate plays player1. UNKNOWN retains observed interior search transitions
but supplies no final draw target. Generic qsearch is rejected; all Generic
queries use qdepth0. Owned declarations, including LOSS, remain real choices;
RESTART/NO_CONTEST never become draws. Incomplete queries pay visited nodes,
produce no root action/training receipt and leave the full session unchanged.

Twenty-four new regression cases independently check the forward lambda sum,
real Chess mate learning, full promotion/drop/auxiliary/history replay, all
declaration outcomes, cancellation, terminal-on-last-ply, and budget censorship.
Twenty-three retained learner/adapter regressions also pass. A transient legacy
comparison matched60 real search receipts and20 complete episode updates exactly
apart from elapsed time; old pinned source files were not modified.

## One-rule semantic exploration, 2026-10-21

Decision question: does this common path obtain nonzero TD updates and actual
terminal play evidence when promotion, base-hand drops and temporary auxiliary
state coexist, or does the chosen distribution supply no useful learning signal?
This is algorithm reuse on one rule, not cross-rule knowledge transfer, an
independent holdout, general strength, or a claim about amateur play.

Input: `data/incremental_semantic_pilot_20261021.json`, a balanced-material
six-actor8x8 stress rule derived from existing semantic fixtures. Two R per
player can capture to hand and drop under a zone guard; a semantic diagonal
move changes R to TP and creates an expiring global right. That right is carried
through the real game even though this fixture has no action conditioned on it.
Movement/geometry can be asymmetric; evaluation balances candidate color.

Configuration: seed8173; declared board-R unit; remaining coordinates initially
uniform[.5,1.5], with no human material prior. Uniform-weight opponent; D2/q0,
8192 nodes/query,100000 nodes/game,H128. At most128 training episodes and32
evaluation root families x2colors x2profiles. Both learned and initial profiles
use the same per-game resources, roots and search-order seeds. Family profile
order alternates. Fresh random opening paths have2–8 moves; these fixture-based
paths are exploratory, not independently withheld positions or rule families.

Cap:1M combined candidate/foe training nodes,1M evaluation nodes,1800 seconds
overall, with training restricted to the first900 seconds. Missing slots and
UNKNOWN remain explicit. The root D2 calibration visited94 nodes in.091s;
full replay, opening construction and branch variation add cost. Projected
all-in execution stays below the fixed30-minute fuse and120-minute consultation
threshold. No result-driven extension or top-up is permitted.

The20-second lifecycle smoke completed2 training episodes and4 evaluation slots
in9.502s /9207 nodes; all four evaluation games were UNKNOWN and no update
occurred. Those H16 smoke outcomes do not establish learnability or strength.
The longer exploratory run uses H128 as specified above and remains a separate
new study, not a retry of any frozen experiment.

Reproduction (run from this checkout; raw traces stay ignored):

```powershell
.venv\Scripts\python.exe -m scripts.incremental_learning --rules docs/research/data/incremental_semantic_pilot_20261021.json --unit R --seed 8173 --train-episodes 128 --eval-pairs 32 --train-nodes 1000000 --eval-nodes 1000000 --seconds 1800 --horizon 128 --depth 2 --query-nodes 8192 --game-nodes 100000 --output artifacts/incremental-semantic-pilot-20261021
```

Only compact results belong here after completion. The reported completion
bound treats unknown or missing payoffs as possible[-1,1]; it is not a confidence
interval. A nonzero update, changed action, or predictive score is not W/L/D.
