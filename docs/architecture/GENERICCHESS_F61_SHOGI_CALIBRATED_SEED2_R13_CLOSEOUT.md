# F61 Standard-Shogi calibrated optimizer-seed screen — R13 closeout

## Scope and authority

R13 tested the Chat-ordered optimizer-seed replication only. It reused the
existing 24 persisted Standard-Shogi roots and their 157 q20/base-Q rows,
which were generated under data seed 59012. The fit seed changed to 59013;
this is not an independent data-seed replication. No roots, objective,
architecture, search budget, alpha method, or prior Arena games were changed.

- Ruleset: `B_CANONICAL_STANDARD_SHOGI`
- Parent checkpoint: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Training: `PAIRWISE_RANKING`, width 32, regularization `1e-3`, 600 steps
- Training seed: `59013`
- Persisted roots: `24`; training actions: `157`
- Code checkpoint: `ca39425eea8aa83d2edf1e10a63027dcf433e6b1`
- Compute plan SHA: `a348a357fd41177be5fac058d5420c128dcd81f3a55c0864aaecfdd2f00dcebb`
- Resource envelope SHA: `c9bb5d8ab439426bfc948c9087e91dd835bdea652f4e3cca24edb9fc2c1d6fd1`
- Chat approval request: `GENERICCHESS-20260913-163708-c4a03088`
- Heavy run: `f61-shogi-seed2-r13-one-pair-09b02ec8c58a`

## Fit and scalar calibration

The seed-59013 child checkpoint is
`e901fe90a963b6ae31e2d954290c9b42a94a6ec2c526245bcc702573c556908f` with
model SHA256
`0600e7ca61999127f255c2cfb2fc4be17ec03a823b210aaccd1d0ee925ff4de2`.

The deterministic no-intercept scalar was recomputed from the seed-59013
predictions and the fixed residual targets:

- `alpha = 0.04417702070586609`
- calibrated child checkpoint:
  `7c25f0d6475f00735a0ad14fe6bc24f5b46936c674b39e7dc455770c55338c12`
- calibrated model SHA256:
  `53baa4532a19c3ca19addde9fa5889489dfdd5a6e87b6b78fdcefb5d54db35d6`
- actual calibrated prediction versus `alpha * original_prediction` maximum
  absolute error: `2.2737367544323206e-13`
- ranking agreement: `292/349 = 0.836676217765043`

The frozen four-opening gate used seed 620700, 2,000 nodes, depth 12, and
TT 8 MiB. All four calibrated actions differed from the parent, so the Arena
stage was admissible. Three of the four calibrated actions matched the
uncalibrated seed-59013 child; the fourth changed both child variants.

## Fresh Arena screen

Exactly one fresh role-swapped pair ran at opening seed `620703`, with the
approved 2,000 nodes/move, depth 12, TT 8 MiB, and one worker. Both games
ended in checkmate:

| game | calibrated-child owner | winner | plies |
|---|---:|---:|---:|
| owner-0 | 0 | 0 (child) | 163 |
| owner-1 | 1 | 0 (parent) | 105 |

The pair score is `[0.5]`, mean `0.5`, with `0` better, `1` tied, and `0`
worse pairs. Game W/D/L is `1/0/1`; directional failure is false. Under the
Chat order's rule, the screen meets the `>=0.5` threshold and returns before
any three-pair confirmation expansion. This single pair is not a strength
estimate and should not be pooled with the prior seed-59012 calibrated child
as if it were the same candidate.

## Verification and disposition

The focused F61 contract tests passed: `10 passed`. The code checkpoint was
published at the exact synchronized sandbox SHA above. R13 is complete and
returns to Chat/Supervisor for the next work order; no promotion or automatic
expansion is authorized by this report.

