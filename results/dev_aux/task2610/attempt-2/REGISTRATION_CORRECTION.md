# task2610 attempt 2 — runner schema correction

Attempt 1 (top-level task2610 `registration.json`) failed before any output slot: the reused task2609 evaluator requires `model_result_sha256`, while the first task2610 registration used only the equivalent `models_sha256`. The original registration, plan, root manifest and failure are preserved. `attempt-1-failure.json` records the exact exception, zero output rows/nodes and source hashes.

Attempt 2 uses this directory's byte-identical copies of the parent evaluation plan and root manifest. Its separate registration adds the expected `model_result_sha256` alias and pins the parent registration/failure, plan, root manifest, frozen model result, all experimental sources and this attempt's runner. The experiment itself is unchanged: same four rules, four parameter seeds, first 16 preclassified VALID_AFTER_TARGET roots/rule, three endpoints, colors, foe, search budget and 1200-second cap. The reused evaluator will preflight all 64 roots before writing `eval-started.json`.

This is a runner-contract repair only. No retraining, root replacement, cap change, or fitness data was produced by attempt 1.
