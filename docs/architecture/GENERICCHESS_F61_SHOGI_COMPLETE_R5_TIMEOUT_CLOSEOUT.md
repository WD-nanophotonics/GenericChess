# F61 Standard Shogi first-seed completion R5 timeout closeout

Date: 2026-09-13

## Exact run binding

- Published sandbox: `3d9eaaaad78166177bdb331fa79314b77c225374`
- Compute plan: `f61-shogi-first-seed-complete-r5-20260913-v1`
- Plan SHA256: `ae8f564cfe290ab21c39b053488e88ad590f9a8c86705c47bd752a7e63f6dd2e`
- Envelope SHA256: `9a8c1a7844a9e2feb1fc7fc92c352c8c497f6411f26a00ad70752638e752f4b9`
- Command: `.venv\\Scripts\\python.exe scripts/f61_gen0_gen1_strength_triage.py --ruleset B_CANONICAL_STANDARD_SHOGI`
- Heavy run: `f61-shogi-complete-r5-b68aef16a47d`
- Heavy status: `timed_out`
- Timeout reason: `hard_wall_minutes_exceeded`
- Hard wall: 30 minutes

Chat approved this exact plan. The run used the declared 2-CPU/1-lane
`small_or_medium` envelope. No second ruleset, alternate seed, or extra Arena
was started.

## Durable evidence boundary

The matching real 9x9 Standard-Shogi manifest and two previously complete
role-swapped pairs were validated and reused. R5 completed one additional real
game, `game-000002-owner-0.json` (pair 2, 102 plies, checkmate, winner 1,
child checkpoint `35462d58263581a0f456d863bcd29a78ae82b9d90a82147404bff2346833d1a5`).
Its role-swapped mirror did not reach a terminal checkpoint before the hard
wall. The real progress directory therefore contains five completed game files:
four games from pairs 0 and 1 plus one game from pair 2; pair 3 and the mirror
of pair 2 remain missing. No aggregate F61 result was serialized, so this run
does not support a four-pair score, W/D/L summary, model comparison, or
directional conclusion.

The separate fingerprint directory containing four synthetic smoke games was
excluded, as required by the plan.

## Correction to the R4 closeout

`GENERICCHESS_F61_SHOGI_GAME_RESUMABLE_R4_TIMEOUT_CLOSEOUT.md` incorrectly
described all eight files as real Standard-Shogi games. The durable evidence
shows that R4 had four real games (two real pairs) and four synthetic smoke
games. R5 used the real manifest to exclude those smoke files; this report is
the corrected accounting and supersedes that factual statement. The R4 report
also correctly recorded that no aggregate result had been produced.

The completed real files and checkpoints remain valid ignored-runtime evidence
for the next fresh Chat work order. No Chess/generated arm, seed 2/3, Gen2,
R7, larger Arena, or replacement progress format was started.
