# F61 Standard Shogi final-pair R7 timeout closeout

Date: 2026-09-13

## Exact run binding

- Published sandbox: `52182fb134c5af416efa10beb2f703429d9c61ee`
- Compute plan: `f61-shogi-first-seed-final-pair-r7-20260913-v1`
- Plan SHA256: `70e66fa95c5165efd65449a7784e3913e417ea45cdf4fe9986fd251b956c7f77`
- Envelope SHA256 (flow-normalized): `3dca1a184354affc345cea3aff70898762abd9a56bf6c41a146bc80f810de1b4`
- Command: `.venv\\Scripts\\python.exe scripts/f61_gen0_gen1_strength_triage.py --ruleset B_CANONICAL_STANDARD_SHOGI`
- Heavy run: `f61-shogi-final-pair-r7-ed0f09ed45d8`
- Heavy status: `timed_out`
- Timeout reason: `hard_wall_minutes_exceeded`
- Hard wall: 30 minutes

Chat explicitly approved this exact plan and the registered Supervisor audited
the `small_or_medium` envelope. No alternate ruleset, seed, or Arena was run.

## Durable evidence boundary

The matching real 9x9 Standard-Shogi manifest and six validated real games
were reused. R7 completed `game-000003-owner-0.json` (pair 3, owner 0,
checkmate, 255 plies), bringing the real progress directory to seven
completed games: pairs 0, 1, and 2 are complete and pair 3 has only its
owner-0 game. The final role-swapped `game-000003-owner-1.json` did not reach a
terminal checkpoint before the hard wall.

No aggregate F61 result was serialized. This run therefore does not support a
four-pair score vector, W/D/L summary, model comparison, or directional
conclusion. Exactly one real game remains, and the existing game-level runner
can resume it without replaying any completed game.

The separate fingerprint directory containing four synthetic smoke games was
excluded. No completed real file was replayed or overwritten.

The seven completed real files and checkpoints remain valid ignored-runtime
evidence for the next fresh Chat work order. No Chess/generated arm, seed 2/3,
Gen2, historical teacher-only R7 experiment, larger Arena, or replacement
progress format was started.
