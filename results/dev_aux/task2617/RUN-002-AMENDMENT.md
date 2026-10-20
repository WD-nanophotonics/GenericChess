# task2617 run-002 amendment

`run-001` remains preserved as `FAILED_PRE_SEARCH_STARTUP`: the evaluator
created its start/binding receipts, then raised `KeyError: ordering_seed_offset`
before the first `TrainingSearch.search` call. Its game/query JSONL traces are
empty and no result or paid nodes exist. See `run-001/startup-failure.json`.

`run-002` repairs only that omitted deterministic tie-ordering input. It takes
`ordering_seed_offset` from the already frozen `task2616/eval-plan.json`
(`972568000`) and pins that source. The evaluator checks the copied value in
both registered plans against the pinned task2616 plan before starting.

The 32 roots, four seeds, four endpoints, uniform foe, 16/16 randomized family
cap allocation, 1,024-slot order, per-slot combined-both-sides caps, 30.72M
maximum paid-node ceiling, 5,400-second global cap, and 900-second reserve are
unchanged. No model, outcome, seed, root, slot or cap was selected or altered
using run-001 outcomes; it has no search/game outcomes. The failed start used
zero search calls and zero paid nodes. `run-002` is a new write-once preregistered
attempt, not an overwrite or continuation of run-001.

The ordering offset fixes deterministic search tie-breaking only. It is not a
learner, foe, root, cap-assignment or evaluation-policy treatment. Science stays
OPEN; UNKNOWN and missing slots remain censored, never draws.
