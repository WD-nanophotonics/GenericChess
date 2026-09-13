# F61 Standard Shogi game-resumable R4 timeout closeout

Date: 2026-09-13

## Exact run binding

- Published sandbox: `a1d6cb62c7ac79006fdd242b8702c330a602a3a3`
- Compute plan: `f61-shogi-game-resumable-r4-20260913-v1`
- Plan SHA256: `2a82d8ebe25d9d344253bbf2a9d061b28d0e72cc378ee86b46b812496eb082f0`
- Envelope SHA256: `facd9a1aeac02b107acf17f4f7e4197062ac39d654edca496ce1495e7c4219fe`
- Command: `.venv\\Scripts\\python.exe scripts/f61_gen0_gen1_strength_triage.py --ruleset B_CANONICAL_STANDARD_SHOGI`
- Heavy run: `f61-shogi-game-resumable-r4-c0ec2962db89`

Chat explicitly approved this fresh plan. The run used the declared
2-CPU/1-lane envelope and 30-minute hard wall. It ended in terminal state
`timed_out` with `timeout_reason=hard_wall_minutes_exceeded` while final result
serialization was still pending.

## Durable evidence boundary

The existing 24 D0 root checkpoints were reused. The game-level Arena
progress directory now contains all 8 complete swapped-color game files (four
complete pairs), each validated by the existing manifest/replay identity
protocol. No game was converted to a draw and no pair was duplicated. The
driver did not persist the aggregate result before the hard wall, so there is
no scientific parent/child model summary, pair-score vector, W/D/L, or
directional conclusion to report from this run.

The game files and roots remain valid ignored-runtime evidence for the next
fresh Chat work order. No Chess/generated arm, seed 2/3, Gen2, R7, larger
Arena, or alternate progress format was started.
