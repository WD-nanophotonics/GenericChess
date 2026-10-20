# Audit implementation notes — task2616

- The frozen `audit.py` expects `weights_after`, absent from the pinned training trace schema. Its first run stopped with `KeyError: weights_after`; the original pinned file is preserved unchanged.
- The retrospective audit v2 was developed against the observed schema. Two initial v2 assertions were over-scoped: one compared a seed's final model with an intermediate game's snapshot; another treated each game's starting weights as the seed's original random initialization. These were corrected to chain game snapshots in order, verify each logged `weights_used` before its update, and compare the replayed final seed state with both the final game and arm snapshots.
- Final full replay passes. The transient assertion failures were audit-code defects, not experiment-run failures; all were retained here for provenance.
