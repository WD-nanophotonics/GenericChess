# F61 Standard Shogi resume R3 timeout closeout

Date: 2026-09-13

## Exact run binding

- Published sandbox: `becbb62b95f14fe578c5e0ddc65f3ea6f2619a5a`
- Compute plan: `f61-shogi-first-seed-resume-r3-20260913-v1`
- Plan SHA256: `b450f87bde1d10a473acecfd97b171e26da80100b31059b02b6f931e316a076e`
- Envelope SHA256: `6a90a7f53cfbd1159665fd80a135078ab00f217dc52af414b2b89a6029f7c5a9`
- Command: `.venv\\Scripts\\python.exe scripts/f61_gen0_gen1_strength_triage.py --ruleset B_CANONICAL_STANDARD_SHOGI`
- Heavy run: `f61-shogi-resume-r3-37e9f48aaf14`

Chat explicitly approved this fresh resume plan. The run reused the existing
24 validated D0 root checkpoints and used the declared 2-CPU/1-lane envelope
with a 30-minute hard wall. The monitor ended it in terminal state `timed_out`
with `timeout_reason=hard_wall_minutes_exceeded` while the fit/Arena phase was
still active.

## Evidence boundary

No result file was produced by this run; stdout and stderr are empty. There is
therefore no parent/child model SHA, pair score, W/D/L, or directional result
to report. This is not a negative seed and must not be scored as one. The
already-completed root checkpoints remain valid and were not deleted or
regenerated. No Chess/generated arm, seed 2/3, Gen2, R7, or larger Arena was
started.

The published driver and valid root checkpoints remain at
`becbb62b95f14fe578c5e0ddc65f3ea6f2619a5a`. A fresh Chat work order is
required before changing the resume resource bound or making another compute
attempt.
