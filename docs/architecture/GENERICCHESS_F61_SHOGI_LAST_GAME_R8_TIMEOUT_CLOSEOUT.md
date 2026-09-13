# F61 Standard Shogi last-game R8 timeout closeout

Date: 2026-09-13

## Exact run binding

- Published sandbox: `7610d2e1853a35b196f062e02862780756ea189f`
- Compute plan: `f61-shogi-first-seed-last-game-r8-20260913-v1`
- Plan SHA256: `f7c6ac7e292092500608afc32ec4a9f2e58dcdfc7f84081597f1ce23e87b3027`
- Envelope SHA256 (flow-normalized): `b053e15f9a908f07f4a60ff175fd7dfb816e42df3d341e0387a53b963600dc45`
- Command: `.venv\\Scripts\\python.exe scripts/f61_gen0_gen1_strength_triage.py --ruleset B_CANONICAL_STANDARD_SHOGI`
- Heavy run: `f61-shogi-last-game-r8-3f5b3e8c7465`
- Heavy status: `timed_out`
- Timeout reason: `hard_wall_minutes_exceeded`
- Hard wall: 30 minutes

Chat explicitly approved this exact plan and the registered Supervisor audited
the `small_or_medium` envelope. No alternate ruleset, seed, or Arena was run.

## Durable evidence boundary

The matching real 9x9 Standard-Shogi manifest and seven validated real games
were reused. R8 attempted only the missing `game-000003-owner-1.json`; it did
not reach a terminal checkpoint before the hard wall. The real progress
directory therefore remains at seven completed games: pairs 0, 1, and 2 are
complete and pair 3 has only owner 0.

No aggregate F61 result was serialized. This run does not support a four-pair
score vector, W/D/L summary, model comparison, or directional conclusion.
Exactly one real game remains, resumable by the existing game-level runner.

The separate fingerprint directory containing four synthetic smoke games was
excluded. No completed real file was replayed or overwritten.

The seven completed real files and checkpoints remain valid ignored-runtime
evidence for the next fresh Chat work order. No Chess/generated arm, seed 2/3,
Gen2, historical teacher-only R7 experiment, larger Arena, or replacement
progress format was started.
