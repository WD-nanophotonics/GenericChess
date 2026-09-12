# GenericChess F94-R3 nonbinding depth-calibration PREP

Status: result-free protocol preparation only. No R3 Arena, Heavy computation,
Stage 1, 216-game schedule, tuning, ruleset change, or adjacent evaluation was
run or authorized.

`docs/architecture/GENERICCHESS_F94_R3_NONBINDING_DEPTH_CALIBRATION_PREP.json`
is an independent calibration authority. It preserves the R2 READY controls,
evaluator/checkpoint identities, three frozen tape corpora, opening index 0,
4096-vs-256 node budgets, one role-swapped pair per tape, 8 MiB TT,
single-worker execution, and boundary compute-zero short circuit. Its only
measurement-design change is `max_depth: 64` instead of 12.

R2 is explicitly recorded as `OBSERVED_NOT_POOLABLE`: its result is evidence
that the old protocol depth-censored Western Chess, not a sample that can be
combined with any later R3 confidence interval. Any R3 execution still needs a
new explicit Chat and registered-Supervisor approval bound to a new compute
plan, resource envelope, exact sandbox SHA, and command argv.
