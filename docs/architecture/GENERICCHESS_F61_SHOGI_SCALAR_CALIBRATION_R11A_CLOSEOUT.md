# F61 Standard Shogi scalar-calibration screening R11A

Date: 2026-09-14

## Exact binding

- Work order: `GENERICCHESS-F61-SHOGI-SCALAR-CALIBRATION-CORRECT-R11A`
- Published sandbox: `5934bdf0d67591567d379069eded83ec2e178eac`
- Compute plan: `f61-shogi-cal-r11a-one-pair-20260913-v3`
- Plan SHA256: `f8b974171a751267c0d7596a30df9b881f80edbce5c22134328ed49c1e7f25be`
- Envelope: `f61-shogi-cal-r11a-one-pair-20260913-env-v3`
- Envelope SHA256: `8f79f66f919192df0d8b8863275677de781f737b921b0af24d94c77c7d72de49`
- Chat approval SHA256: `9e93a2b710bf29b16c1b45e165c17ac1c50920579272c019b827feda7b4eefa2`
- Heavy run: `f61-shogi-cal-r11a-one-pair-v3-abe8d63be256`
- Heavy status: completed, exit code 0
- Command: `.venv\\Scripts\\python.exe scripts/f61_pairwise_scale_calibration.py --run-arena --fresh-arena-seed 620701 --arena-pairs 1`
- Resource envelope: one role-swapped pair (two games), 2,000 nodes/move, depth 12, TT 8 MiB, 75-minute hard wall

## Calibration and pre-Arena gate

The exact seed-59012 parent, original child, and 24 persisted roots were
reconstructed.  No roots were collected and no model was retrained.  The
least-squares no-intercept coefficient was:

`alpha = 0.04101897806310457`

The corrected intervention scales both `output_weights` and `output_bias`.
On all 157 existing feature vectors, the corrected checkpoint's actual
prediction equals `alpha * original_prediction` with maximum absolute error
`1.7053025658242404e-13`.  The four frozen seed-620700 parent/original/
calibrated searches remained behaviorally nontrivial: calibrated action
differed from parent on all four openings (and matched the original child on
each opening).

- Parent checkpoint: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Original child checkpoint: `35462d58263581a0f456d863bcd29a78ae82b9d90a82147404bff2346833d1a5`
- Corrected calibrated child checkpoint: `d12326023813e9cfd1fa91ad5203f1d3603ec34b1e7b65005cc45a192a366889`
- Corrected calibrated model SHA256: `f0a953c3ce0e74a3c22b41b5fbac6e77bb3f32d6aa83b1b12a911270a6ee63a5`

## Fresh actual-play screening

The fresh role-swapped pair used opening seed `620701` at the unchanged full
budget.  Both games ended by checkmate: `game-000000-owner-0.json` in 52
plies and `game-000000-owner-1.json` in 63 plies; the calibrated child won
both games.

- Pair score: `[1.0]`
- Mean pair score: `1.0`
- Child better / tied / child worse pairs: `1 / 0 / 0`
- Child game W / D / L: `2 / 0 / 0`
- Directional-failure flag: `false`
- Persisted aggregate: `.generic_chess_flow/f61-gen0-gen1-strength-triage/pairwise_scale_calibration.json`

This is an actual-play screening gate, not a precise win-rate estimate.  The
score is at least 0.5, so the scalar calibration is not rejected; per the
work order it only warrants returning to Chat/Supervisor for a decision before
any larger confirmation.  No second alpha, new training, Chess/generated
rules, Gen2, teacher-only work, or broader sweep was run.
