# F61 Standard Shogi lean R2 timeout closeout

Date: 2026-09-13

## Exact run binding

- Published sandbox: `e0042990a79eb3df5ccdfc8c04c43ec14ce424e0`
- Compute plan: `f61-gen0-gen1-shogi-lean-r2-20260913-v1`
- Plan SHA256: `2f433ed9993978f65cbe15ea7b33cfc9ec36173e248f274a45b32acd5edc4938`
- Envelope SHA256: `3b381a280b49701005860a8e8c5ef8395b33b88a23f6aa63cdf91780b70a8fcc`
- Command: `.venv\\Scripts\\python.exe scripts/f61_gen0_gen1_strength_triage.py --ruleset B_CANONICAL_STANDARD_SHOGI`
- Heavy run: `f61-shogi-lean-r2-8047149c4e3e`

Chat explicitly approved the compute decision. The run used the declared
2-CPU/1-lane envelope and the monitor's 45-minute hard wall. It ended in the
terminal state `timed_out` with `timeout_reason=hard_wall_minutes_exceeded`.

## Evidence and boundary

All 24 Standard-Shogi D0 roots completed and were durably checkpointed under
ignored runtime, each bound to the ruleset fingerprint, root identity, parent
checkpoint, training seed, and frozen search-budget signature. The driver did
not reach model fitting/Arena result persistence before the hard wall. The
Heavy stdout and stderr logs are empty, and no result file from this run
exists. The similarly named selector-test JSON is not scientific evidence.

Therefore this run supplies no Gen0-to-Gen1 playing-strength result and no
directional conclusion. It must not be counted as a failed seed. No retry,
parameter expansion, Chess arm, generated arm, seed 2/3, Gen2, R7, or larger
Arena was started.

The driver-local repair and focused regression remain published at
`e0042990a79eb3df5ccdfc8c04c43ec14ce424e0`; the pre-Heavy focused test passed
(`tests/test_f61_gen0_gen1_strength_triage.py`, 4 passed). A fresh Chat work
order is required before any new compute attempt or further optimization.
