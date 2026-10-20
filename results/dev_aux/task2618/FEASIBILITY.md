# DEV_AUX task2618 — TreeStrap/TDLeaf Chess comparison feasibility

**Status: feasibility audit only.** No learner-comparison protocol is
registered and no training or evaluation search has started.

## Decision and estimate

The four-endpoint standard-Chess comparison projects to **95.77 minutes**,
below the 120-minute Dot-assessment threshold and the frozen 110-minute
all-in cap. `feasibility.py` now estimates each 4M-node training arm by scaling
the observed 400k-node cost-only receipts from the shared AlphaBeta/Receipt
path: 565.267s TreeStrap, 554.453s TDLeaf, and 531.339s finite WDL. It adds the
slower complete 1,024-slot evaluation (2,225.822s), a 25% runtime margin, and a
900s setup/audit reserve. The calculation is reproducible from the exact pins
in `feasibility.json`.

Proposed hard phase caps remain 2,100s for all training, 3,600s for all
evaluation, and one 900s setup/audit reserve: 6,600s total (110m). These caps
are not permission to extend a run. Preserve unfinished arms/slots and UNKNOWN
if a cap binds; do not resume or top up under a new name. The estimate scales
historical measurements and is not a runtime guarantee. It remains a planning
estimate until the exact learner runner, evaluator, analyzer, and write-once
registration bundle are frozen and cost-checked.

## Source and outcome boundary

Training timings come from task2612 attempt-4 and task2618's shared WDL scan,
both complete cost-only receipts on the shared AlphaBeta/Receipt candidate-vs-
fixed-foe path. They record no outcomes, coefficients, or fitted weights. The
4M-node projections assume approximately linear scaling from 400k paid nodes;
root mix, later runner changes, and system load can change actual time. The
evaluation estimate uses the slower of the complete task2616 and task2617
1,024-slot panels. This calculator reads only aggregate node/time fields and
source hashes, never game labels.

## Remaining launch gate

Before registering or launching, freeze and hash the precise arm and episode
order, training runner, evaluator, capped family map, analysis, source/runtime
pins, and write-once output paths. Complete end-to-end replay and invariants;
then recompute the projection from the final sources. If expected duration
reaches 120 minutes, request Dot's necessity assessment before registration or
launch. Otherwise proceed only within the existing 110-minute cap. This audit
does not authorize search or establish learning efficacy.
