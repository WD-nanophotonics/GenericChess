# Task 2601 — post-hoc TRAIN-root concentration audit

**Question.** How concentrated are the already frozen task2595 TRAIN root draws when complete serialized histories, rather than nominal family IDs, define clusters?

**Scope.** Read only the `train` array of the committed task2595 `root-manifest.json`. Canonicalize each complete `record` as compact, sorted-key JSON. Report row-weighted unique-history count, multiplicity concentration, terminal mass, action-depth counts and first-action frequencies.

**Timing / inferential status.** This follow-up is explicitly post-hoc: the descriptive concentration was first explored during session 4bb409e8 before this reproducibility note was written. It is not preregistration, hypothesis confirmation, an admission gate, or inferential evidence. The Simpson concentration equivalent is reported only as a compact summary of row-frequency concentration; it is not an independent sample size.

**Exclusions.** The audit must not read EVAL rows, W/L/D outputs, scores, games, learner weights, or held-out logs. It must not modify or reopen task2595, generate roots/rules, select replacements, start fitness, or extend a cap.

**Expected evidence / done condition.** A small deterministic script, its JSON output bound to the source SHA, and a concise report stating limits. Re-run once from this frozen manifest and verify the committed output against the report.
