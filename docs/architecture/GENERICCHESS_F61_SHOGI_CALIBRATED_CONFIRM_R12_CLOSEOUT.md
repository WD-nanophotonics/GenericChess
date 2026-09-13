# F61 Standard Shogi calibrated-child confirmation R12

Date: 2026-09-14

## Exact binding

- Work order: `GENERICCHESS-F61-SHOGI-CALIBRATED-CONFIRM-R12`
- Published sandbox: `4e21cca29bfa8844c6787f9836a1c23d03d224a6`
- Compute plan: `f61-shogi-cal-confirm-r12-20260914-v1`
- Plan SHA256: `8aed66a56ab974fa0a248ac21ff05dedc8925c0cd785053fc91a4ccbe810a659`
- Envelope: `f61-shogi-cal-confirm-r12-20260914-env-v1`
- Envelope SHA256: `3d39bdfe901204b212ca45f97a52ee64e80e84d9d33faecbf8ed438d0c366df6`
- Heavy run: `f61-shogi-cal-confirm-r12-ca8b23d80ee7`
- Heavy status: completed, exit code 0
- Actual driver wall: `4954.97115707397` seconds (`82.5828526178996` minutes)
- Command: `.venv\\Scripts\\python.exe scripts/f61_pairwise_scale_calibration.py --run-arena --fresh-arena-seed 620702 --arena-pairs 3`
- Budget: 2,000 nodes/move, depth 12, TT 8 MiB, workers 1; six new games

The parent and corrected calibrated child remained fixed.  No roots were
collected, alpha was not refit, and no training or evaluator/search setting
changed.

## New three-pair block (seed 620702)

All six new games completed by checkmate:

| pair | owner 0 game | owner 1 game | pair score |
|---|---|---|---:|
| 0 | child win, 83 plies | child loss, 63 plies | 0.5 |
| 1 | child win, 113 plies | child win, 110 plies | 1.0 |
| 2 | child loss, 116 plies | child win, 102 plies | 0.5 |

The new block therefore has pair scores `[0.5, 1.0, 0.5]`, mean `0.666666666666667`,
child better/tied/worse `1 / 2 / 0`, and game W/D/L `4 / 0 / 2`.

Persisted aggregate: `.generic_chess_flow/f61-gen0-gen1-strength-triage/pairwise_scale_calibration.json`.

## Combined four-pair evidence

The prior R11A screening pair (seed 620701) is kept as prior evidence with
pair score `[1.0]` and game W/D/L `2 / 0 / 0`.  Appending it to the new block
gives calibrated-child pair scores `[1.0, 0.5, 1.0, 0.5]`:

- Mean pair score: `0.75`
- Child better / tied / child worse: `2 / 2 / 0`
- Game W / D / L: `6 / 0 / 2`

The combined mean is above 0.5 and better pairs exceed worse pairs, so the
specified rule classifies this as a provisional Standard-Shogi Gen1 success.
This is not a claim of final strength from only four pairs; the next lawful
step is a second independent training-seed replication after returning to
Chat/Supervisor.  No replication, Chess/generated arm, Gen2, teacher-only
experiment, reduced-budget run, or broader sweep was started in this session.
