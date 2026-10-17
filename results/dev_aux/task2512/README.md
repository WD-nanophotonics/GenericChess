# Current same-search learning-method experiment

Opt-in research only. See [method](../METHOD_20261017_88.md) and
[report](../SEGMENT_20261017_88.md) for actual results and limits.

- `train.py` runs retained episode-TD and transformed mean-TreeStrap under the
  same material-only plainD2 search, all4initials and 1Mnode ceilings.
- `plan.json` was frozen before TRAIN. Source bytes are pinned as executed.
- `../task2513` registers endpoint+midpoint actual-outcome validation before any
  deployment fitness; `../task2516` registers a matched different-foe panel.
- `../task2514` independently reconstructs every Tree interval gradient and TD
  forward credit, all actual legal histories, budgets and fixed search samples.

Tree updates STATIC internal-state estimates; TD differentiates the returned
PVleaf. One-sided intervals are not exact targets. Same numeric eta is not an
equated update norm/unit. This is a retained transformed/mean variant, not the
linear/summed historical TreeStrap reproduction. No human-price labels are used.
UNKNOWN is not draw; actual full-rule W/L/D evaluates strength. All seeds, failed
query nodes, horizon censors and missing planned games are retained.

Closed producers reject existing started markers. Never reset them or extend
caps to repeat a favorable point. Execute a NEW registered directory for a new
premise. Exact source/data are in DELTA_REPRO_20261017_88.zip; use extraction for
raw source-pin audits because direct Git publication may normalize LF/EOF.
External dependencies are the existing chess/pytest libraries. Fresh-replay
receipt specifies executed checks; it does not claim new independent training.

The same learner/search interfaces can use a full rule environment, but this
experiment is standardChess. Future Generic scoring uses the NEW typed
`task2511.ScoringSessionEnv`; the frozen legacy2492.SessionEnv mapped non-scoring
RESTART/NO_CONTEST to zero and remains explicitly historical. Do not silently
replace hand/base/promotion/history semantics or owned LOSS declarations.
No new Generic training, Core API, solver or product/default changes here.
