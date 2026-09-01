# ADR-109 — F41 semantic material-prior corrective

- Status: F41 Corrective R1 audit complete; no production integration authorized
- Work order: `GENERICCHESS-F41-RULE-DERIVED-MATERIAL-PRIOR-AND-SIGNAL-UTILIZATION-CORRECTIVE`

F41 is an audit/prototype boundary. It freezes a compiled-IR ordinary-movement
capability source, legacy compatibility controls, Western and Standard-Shogi
health gates, a parameter-free drop deployment index, and F42 mapping. No
production evaluator, search, Native, rules, or learning code may change.

The corrective audit orients source coverage as semantic targets minus legacy
targets, with legacy-only coverage retained separately. Western Pawn has no
legacy movement atoms while its one-step and capture movement is present in
semantic actions; the semantic-only coverage therefore makes Pawn raw
capability positive and removes the normalization floor, but the unchanged
normalization still misses the frozen Western ratio bands. Standard Shogi is a
material positive control under the complete cosine, Spearman, pairwise
ordering, and 0.8–1.0 hand/board gates, while its current droppable base-type
deployment index is uniform, so the drop signal is not independently
informative. Leap-only, ray-only, and hybrid leap/ray compatibility controls
are all executable gates; hybrid raw deltas remain diagnostic because the
semantic path model is richer than the legacy scalar score. The corrected
classification is `SEMANTIC_MATERIAL_PRIOR_INSUFFICIENT` →
`F42_SEMANTIC_CAPABILITY_PRIOR_DIAGNOSIS`.
