# Active incremental learner and frozen87 entries

The reusable material model and episode-frozen TDLeaf update are
`../task2492/learning.py` and `../task2492/episode.py`. Search receipts carry the
selected principal leaf's features; actual terminal leaves have zero derivative,
while earlier eligibility remains. This learner updates after EVERYepisode,
without waiting to select a winning price grid candidate. W/L/D evaluates actual
strength; a search score is a training target, not an actual match reward.

Current TRAIN search: `../task2504/search.py`, with coefficient-independent
SHA256(seed,action-path) order. Both arms use the SAME full-width D2 normal
search. Plain mode is the active cheap baseline. The bounded q2 control counts
ALLextensionplies including forced evasions: at qply>=2 a noncheck node can use
a static leaf, even with captures remaining. In check all legal evasions continue;
resource exhaustion rejects the whole query. Earlier optional-only wording is
corrected in `../task2508/q2-semantic-scope.json`; frozen sources remain unchanged.
This is not full quiescence, exact WDL or a mate prover prerequisite.

`train.py` records every query/PV/prediction/gradient, actual START/MOVE/END,
fixed episode weights and final update. `../task2507/evaluate.py` evaluates all
initial/final weights under common plainD2 versus a fixed uniform foe.
`../task2510/curves.py` evaluates every preregistered quarter-budget snapshot on
separate roots, with one shared physical initial baseline perseed/family/role.
No checkpoint/seed/price is selected from these now-exposed families.

All producer directories are occupied one-shot evidence. Do NOT delete/restart
or extend their caps. For a NEW study, create a NEW output directory and plan,
pin its actual sources, predeclare all arms/roots/costs before fitness, and adapt
the small producer's OUT/reference paths. Existing cap failures and missing slots
remain original. Runs estimated>=120minutes first receive Dot assessment.

For closed validation, extract the exact87capsule for raw byte pins. Then use:

```text
python -m pytest -q results/dev_aux/task2492/test_learning.py results/dev_aux/task2492/test_episode.py results/dev_aux/task2501/test_search.py results/dev_aux/task2504/test_bounded.py --import-mode=importlib
python -m results.dev_aux.task2508.training_audit
python -m results.dev_aux.task2508.evaluation_audit 2507
python -m results.dev_aux.task2508.evaluation_audit 2510
python -m results.dev_aux.task2508.behavior_audit
```

These are data/source replays, not new training or an independent engine match.
chess1.11.2 is the separately installed GPL-3.0+ rule authority; pytest tests it.
Plotting is optional, using matplotlib3.10.7/NumPy1.26.4 with an explicit private
MPLCONFIGDIR. Neither dependency source nor private account logs are bundled.
Git text can normalize LF/EOF; recorded byte pins refer to immutable raw ZIPs.

The retained one-sided TreeStrap implementation is a transformed mean-batch
variant, not a literal paper reproduction. Its direct total-cost comparison to
this episodeTD, faithful Beal-Smith reproduction, stable material ratios and full
Generic learning remain OPEN. `SessionEnv` already connects the same model/search
to full GameSession state/history and board-current/hand-base channels; qsearch
is unsupported there. Four interface demonstration steps are not generic
learning success. Product defaults/UI and PRIMARY integration are unchanged.

Generic terminal correction87: legacy SessionEnv remains frozen evidence and
mislabels RESTART/NO_CONTEST as0. Use ../task2511/generic.py ScoringSessionEnv
for future generic work: non-scoring results raise NonScoringTerminal and require
an explicit caller policy. They are neither draws nor numeric UNKNOWN targets.
Seven actual GameSession regressions qualify this guard; no generic training
was added and all current Chess byte pins remain unchanged.
