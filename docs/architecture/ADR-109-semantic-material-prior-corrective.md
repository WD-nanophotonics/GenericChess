# ADR-109 — F41 semantic material-prior corrective

- Status: F41 audit complete; no production integration authorized
- Work order: `GENERICCHESS-F41-RULE-DERIVED-MATERIAL-PRIOR-AND-SIGNAL-UTILIZATION-CORRECTIVE`

F41 is an audit/prototype boundary. It freezes a compiled-IR ordinary-movement
capability source, legacy compatibility controls, Western and Standard-Shogi
health gates, a parameter-free drop deployment index, and F42 mapping. No
production evaluator, search, Native, rules, or learning code may change.

The audit found the expected source omission: Western Pawn has no legacy
movement atoms while its one-step and capture movement is present in semantic
actions. Reconstructing ordinary capability from compiled IR makes Pawn raw
capability positive and removes the normalization floor, but the unchanged
normalization still misses the frozen Western ratio bands. Standard Shogi is a
material positive control (candidate board-value cosine 1.0 versus current),
while its current droppable base-type deployment index is uniform, so the drop
signal is not independently informative. Pure atom compatibility controls are
exact; mixed leap/ray controls are reported separately. The resulting boundary
is `SEMANTIC_MATERIAL_PRIOR_CROSS_RULESET_FAILURE` →
`F42_SEMANTIC_MATERIAL_PRIOR_COMPATIBILITY_DIAGNOSIS`.
