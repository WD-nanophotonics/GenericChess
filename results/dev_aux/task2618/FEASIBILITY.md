# DEV_AUX task2618 — TreeStrap/TDLeaf Chess comparison feasibility

**Status: feasibility audit only.** No roots, seeds, model arms, outcomes or
updates were selected or executed. No protocol is registered.

## Decision and estimate

The proposed four-endpoint, standard-Chess comparison appears feasible below
the 120-minute Dot-assessment threshold under an all-in cap of 110 minutes.
The reproducible calculation in `feasibility.py` is 93.47 minutes: it sums
observed 4M-node training times for TreeStrap (532.797s), TDLeaf (the slower of
two historical measurements, 513.875s), and the finite-WDL control (494.221s),
then adds the slower complete 1,024-slot evaluation (2,225.822s), a 25% runtime
margin, and 900 seconds for setup/audit. The 1,024 evaluation slots are shared
across initialization and three learned endpoints (TreeStrap, TDLeaf, WDL).

Proposed hard phase caps, if the design advances, are 2,100s for all training,
3,600s for evaluation, and a single 900s setup/audit reserve: 6,600s total
(110m). These caps are not permission to extend a run. Preserve unfinished
arms/slots and UNKNOWN if a cap binds; do not resume/top up under a new name.
The estimate uses historic runners and node mixes and is not a runtime
guarantee. It is not the registration. Recompute after root/seed/runner source
pins are frozen; if expected total reaches 7,200s, obtain Dot's necessity
assessment before registration/start.

## Source-bound inputs

`feasibility.py` reads only aggregate cost receipts and emits source SHA-256s.
Inputs: task2616 TreeStrap training and complete four-endpoint evaluation;
task2594 TD training; task2568 TD and WDL training costs; task2617's complete
four-endpoint 1,024-slot evaluation-cap panel. The slowest TD receipt and the
slower of the two full evaluation receipts are used. No outcome labels are read
by the calculation. The WDL training time is from the historical
`TrainingSearch` runner, while the proposed common learner path uses task2612's
`AlphaBeta`/`Receipt`; its runtime under that final adapter remains unmeasured.
Thus 93.47m is a conservative projection, not the final source-bound run
estimate. Keep the 110m all-in hard cap and remeasure the shared-path WDL arm
before registration; if the revised expected duration reaches 120m, consult Dot
before launch.

This is a useful route selection result: under the measured comparable scale,
the preregistered method comparison does not need to be reduced to a weaker
single-learner smoke test solely to fit the two-hour rule. It does not establish
learning efficacy, nor guarantee the complete run will finish within its cap.

## Still required before registration

1. Freeze the precise four-seed learner arms, initialization pairing, proposal
   rule, opponent and all candidate/foe paid-node accounting.
2. Generate and audit the fresh full-history-disjoint training/evaluation root
   sets against task2594 and all starts used for training. This audit has not
   selected or checked those roots.
3. Pin the final shared-receipt runner, learner implementations, evaluator,
   audit and analysis sources; rerun the cost calculator against the actual
   frozen plan and include any changed engineering/audit work.
4. Register the plan before any outcome exposure. Report training loss only as
   a diagnostic; actual terminal Chess W/L/D is the strength endpoint. Bounds
   remain one-sided, UNKNOWN is censored, and the finite panel is not a
   population estimate.

No Dot request is needed for this feasibility-only audit or a later registered
run whose revised expected all-in duration remains below 120 minutes. A changed
scope or estimate at/above that threshold requires assessment before launch.
