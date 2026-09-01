# F41 semantic material-prior closeout

- H41A published SHA: `3a632b551e82fe8ef191cd9181bae324b0f08266`
- Final audit-tree SHA at generation: `d50aff9b1dcbb11c1ef0f2988517bb48e4e8ce1b`
- H41A manifest SHA256: `6bd7d52b196e7eccb2309f813b6e1417c77ee3a9992e22f0dcfafc8f01084e01`
- Production diff: zero; this checkpoint changes only audit documentation, scripts, and tests.
- Promotion: not requested and not performed.

## Source coverage

| Ruleset | Type | Legacy destinations | Final executable semantic destinations | Ordinary patterns | Conditional patterns | Omitted |
|---|---:|---:|---:|---:|---:|---:|
| Western Chess | K | 64 | 64 | 2 | 0 | 0 |
| Western Chess | P | 0 | 56 | 3 | 3 | 0 |
| Western Chess | N | 64 | 64 | 2 | 0 | 0 |
| Western Chess | B | 64 | 64 | 2 | 0 | 0 |
| Western Chess | R | 64 | 64 | 2 | 0 | 0 |
| Western Chess | Q | 64 | 64 | 2 | 0 | 0 |
| Standard Shogi | K | 81 | 81 | 16 | 0 | 0 |
| Standard Shogi | P | 72 | 72 | 2 | 0 | 0 |
| Standard Shogi | L | 72 | 72 | 2 | 0 | 0 |
| Standard Shogi | N | 63 | 63 | 4 | 0 | 0 |
| Standard Shogi | S | 81 | 81 | 10 | 0 | 0 |
| Standard Shogi | G | 81 | 81 | 12 | 0 | 0 |
| Standard Shogi | B | 81 | 81 | 8 | 0 | 0 |
| Standard Shogi | R | 81 | 81 | 8 | 0 | 0 |
| Standard Shogi | TP | 81 | 81 | 12 | 0 | 0 |
| Standard Shogi | TL | 81 | 81 | 12 | 0 | 0 |
| Standard Shogi | TN | 81 | 81 | 12 | 0 | 0 |
| Standard Shogi | TS | 81 | 81 | 12 | 0 | 0 |
| Standard Shogi | TB | 81 | 81 | 16 | 0 | 0 |
| Standard Shogi | TR | 81 | 81 | 16 | 0 | 0 |

## Findings

- Western cause: canonical Pawn `PieceType.movement_atoms` is empty; Pawn movement is present in semantic actions, so legacy atom normalization produced the F40 floor collapse.
- F41 ordinary capability source uses only compiled leap/ray patterns with one source→target move, no state/slot/postcondition; conditional patterns are recorded separately.
- Western current/candidate Pawn: `0.0` → `1.06228880393026` raw; board `1` → `171`.
- Western candidate Pawn is positive and avoids the floor, but band gate is `False`; normalized ratios: `{"B": 5.847953216374269, "N": 4.5321637426900585, "Q": 14.263157894736842, "R": 8.549707602339181}`.
- Standard Shogi material positive control cosine: `0.9999953399256223`; drop independence: `False`.
- Legacy compatibility: pure atom controls have exact destination coverage and raw deltas ≤1e-9; mixed leap/ray controls are reported without altering production code.
- Drop deployment: `D = drop_freedom * drop_mobility / max(1e-12, all_square_mobility)`; hand candidate is `round(board * hand_weight * D / median_positive_D)` for droppable base types.
- Metamorphic contracts: Western `True`, Standard Shogi `True`.
- Static learning span: no new learning capacity; current board/hand weights remain the only static material parameters.

## Boundary

- Classification: `SEMANTIC_MATERIAL_PRIOR_CROSS_RULESET_FAILURE`
- F42 boundary: `F42_SEMANTIC_MATERIAL_PRIOR_COMPATIBILITY_DIAGNOSIS`
- Flags: `{"DROP_SIGNAL_INDEPENDENCE_AUDITED": true, "F40_MATERIAL_FEATURE_GAP_CONSUMED": true, "NEXT_SEMANTIC_PROFILE_BOUNDARY_SELECTED": true, "SEMANTIC_ANALYZER_LEGACY_COMPATIBLE": true, "SEMANTIC_MOVEMENT_SOURCE_COVERAGE_AUDITED": true, "STANDARD_SHOGI_MATERIAL_POSITIVE_CONTROL_COMPLETE": true, "STATIC_LEARNING_SPAN_AUDITED": true, "WESTERN_MATERIAL_PRIOR_RETEST_COMPLETE": false}`
- Focused tests: 5 passed at audit generation; full regression is a required final workflow gate.
- Historical failure nodes retained exactly: F13 (4), F14 (2), F21 (6), F24F (1); no historical failure was rewritten or promoted.
