# Task2603 — task2594 evaluation-root allocation audit

**Question.** Did each of task2594's four initialization seeds evaluate on the same 128 root families, or on disjoint per-seed blocks?

**Scope.** Read only `eval_families_by_seed` from task2594/root-manifest.json and `slots`/`scope` from task2594/eval-plan.json. Do not open game outcomes, query traces, learner weights, or endpoint summaries. This is a post-hoc record audit, not a new evaluation.

**Expected evidence.** Hash-bound per-seed root IDs, overlap counts, and slot allocation; a report correction that preserves the original outcome and within-slot pairing while narrowing cross-seed interpretation.

**Done condition.** Deterministic audit and focused test reproduce 32 roots per seed, verify whether blocks overlap, and count the frozen color/endpoint slots without inspecting results.
