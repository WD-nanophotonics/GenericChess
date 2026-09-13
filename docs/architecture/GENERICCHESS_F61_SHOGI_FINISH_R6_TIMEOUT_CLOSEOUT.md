# F61 Standard Shogi first-seed finish R6 timeout closeout

Date: 2026-09-13

## Exact run binding

- Published sandbox: `10eedce28495a4b91cffdaf5fb9b11e8b96bfd4f`
- Compute plan: `f61-shogi-first-seed-finish-r6-20260913-v1`
- Plan SHA256: `41cad7bb76b4c697b2d69d2f6a59e80dc1ba5935f514a9bbb3d1b07148790c5c`
- Envelope SHA256 (flow-normalized): `f592ba69e41b730f81fa22a08d8ada637b7bd90ad5c4b8dfb560b5a9fad9cd22`
- Command: `.venv\\Scripts\\python.exe scripts/f61_gen0_gen1_strength_triage.py --ruleset B_CANONICAL_STANDARD_SHOGI`
- Heavy run: `f61-shogi-finish-r6-1be81721d073`
- Heavy status: `timed_out`
- Timeout reason: `hard_wall_minutes_exceeded`
- Hard wall: 30 minutes

Chat explicitly approved this exact plan and the registered Supervisor audited
the `small_or_medium` envelope. No second ruleset, alternate seed, or extra
Arena was started.

## Durable evidence boundary

The matching real 9x9 Standard-Shogi manifest and five validated real games
were reused. R6 completed the missing role-swapped mirror for pair 2:
`game-000002-owner-1.json` (152 plies, checkmate, winner 1), bound to child
checkpoint `35462d58263581a0f456d863bcd29a78ae82b9d90a82147404bff2346833d1a5`.

The real progress directory now contains six completed game files (three
complete role-swapped pairs: pairs 0, 1, and 2). Pair 3 has not started, and
no aggregate F61 result was serialized before the hard wall. Therefore this
run does not support a four-pair score vector, W/D/L summary, model
comparison, or directional conclusion. Exactly two real games remain.

The separate fingerprint directory containing four synthetic smoke games was
excluded. Existing real files were not replayed or overwritten.

The six completed real files and checkpoints remain valid ignored-runtime
evidence for the next fresh Chat work order. No Chess/generated arm, seed 2/3,
Gen2, R7, larger Arena, or replacement progress format was started.
