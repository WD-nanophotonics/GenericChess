# task2636 frozen root channel coverage review

Scope: descriptive replay of the already selected, unregistered task2636 roots. This review does not alter the pool, register a run, or inspect outcomes/search values.

- Root pool SHA-256: `8854a09a406fd2b0c19b50729c22a03b55bc566ab0b4bb9e5e5325a2e1d98718`
- Root audit SHA-256: `091d73c760d81f563e4d2c7f829c71bc8b9eb8bf526544302d540eb13b0eb8d7`
- Feature order: `board:P, board:A, board:B, board:C, board:X, hand:A, hand:B, hand:C, hand:P, hand:X`; identical across all candidates/phases.
- Training: 16 candidates × 120 roots (1,920 total); evaluation: 16 × 16 (256 total).
- Replayed per-root feature nonzero counts directly from the pinned root pool; all counts match `root-channel-coverage.json` exactly.
- Exact rational row-rank of root feature vectors: candidate training ranks `10, 9, 10, 10, 10, 10, 10, 10, 7, 8, 10, 6, 10, 8, 7, 10` (pooled 10); candidate evaluation ranks `10, 3, 7, 8, 6, 9, 8, 8, 5, 5, 3, 3, 8, 5, 7, 6` (pooled 10).

| Candidate | Training root channels | Training absent at roots | Evaluation root channels | Evaluation absent at roots |
|---:|---:|---|---:|---|
| 00 | 10/10 | — | 10/10 | — |
| 01 | 9/10 | hand:X | 4/10 | board:A, board:B, hand:A, hand:B, hand:C, hand:X |
| 02 | 10/10 | — | 7/10 | hand:A, hand:C, hand:X |
| 03 | 10/10 | — | 8/10 | hand:A, hand:X |
| 04 | 10/10 | — | 9/10 | hand:C |
| 05 | 10/10 | — | 9/10 | hand:X |
| 06 | 10/10 | — | 9/10 | hand:A |
| 07 | 10/10 | — | 9/10 | hand:B |
| 08 | 8/10 | board:B, hand:B | 8/10 | board:B, hand:B |
| 09 | 8/10 | hand:A, hand:B | 6/10 | hand:A, hand:C, hand:P, hand:X |
| 10 | 10/10 | — | 3/10 | board:A, board:B, board:C, hand:A, hand:B, hand:C, hand:X |
| 11 | 7/10 | board:A, hand:A, hand:B | 4/10 | board:A, board:X, hand:A, hand:B, hand:C, hand:X |
| 12 | 10/10 | — | 8/10 | hand:A, hand:X |
| 13 | 8/10 | hand:A, hand:C | 5/10 | board:A, hand:A, hand:B, hand:C, hand:X |
| 14 | 7/10 | hand:A, hand:B, hand:C | 7/10 | hand:A, hand:B, hand:C |
| 15 | 10/10 | — | 6/10 | hand:A, hand:B, hand:C, hand:X |

## Interpretation

Six training candidates have at least one channel that is zero on every selected training root (minimum 7/10); fifteen evaluation candidates have at least one channel zero on every selected evaluation root (minimum 3/10). These are support counts at the frozen root boundary only. A zero at a root does not imply that channel stays zero after legal play or receives no TD update; trajectories, search leaves, update timing and gradients were not replayed here. Conversely, a nonzero root count does not establish useful gradient, stable identification, or strength contribution.

The exact root-vector span is full rank when pooling candidates, but several candidate-specific matrices are rank-deficient. This is only a linear-algebra description of these root feature rows; it is not a TD identifiability or learning result. The evaluation roots are a finite panel, not a population sample, and the one shared initialization is not replicated-seed evidence.

Decision: retain the frozen roots and all ten coordinates; do not filter, replace, resample, or claim full per-candidate root support. Report finite-panel limits and keep root support separate from descendant training exposure, completed W/L/D, UNKNOWN, and missing slots. No learner or game evaluation was started.
