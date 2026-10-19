# DEV_AUX task2608 — preserved zero-row evaluator failure

Task2608 was registered as a 1,536-slot evaluation-only run over the frozen task2606 models and task2607-selected roots. The first evaluator invocation reached runner setup but failed before the first slot: the frozen task2608 `eval-plan.json` did not contain `prefix_plies`, although its runner required that key to replay the four-ply prefix.

No game or query row was produced (`eval-games.jsonl` and `eval-queries.jsonl` remain empty). The original registration, plan, source pins, `eval-started.json`, and zero-row artifacts are retained unchanged. The failure is recorded in `attempt-1-failure.json`. No task2608 outcomes are claimed. A corrected, separately registered evaluation-only follow-up is task2609; it adds the missing field, validates every root before result writes, and preserves this failed attempt as provenance.
