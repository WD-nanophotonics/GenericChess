# F61 Standard Shogi first-seed final R9 closeout

Date: 2026-09-13

## Exact run binding

- Published sandbox: `c42c72476aeba7451c98022e9ea32bb7979e6bd4`
- Compute plan: `f61-shogi-first-seed-last-game-long-r9-20260913-v1`
- Plan SHA256: `f1d0181f982d0d813bd75e3a4f972491c920057d07615c73fa897b68aa9fd732`
- Envelope SHA256 (flow-normalized): `7d5eb0c0d02855ead91a64c83fd72fc9330a47302510aafbcf251f6583e1ef2e`
- Command: `.venv\\Scripts\\python.exe scripts/f61_gen0_gen1_strength_triage.py --ruleset B_CANONICAL_STANDARD_SHOGI`
- Heavy run: `f61-shogi-last-game-long-r9-512614db53ae`
- Heavy status: `completed`
- External hard wall: 60 minutes (actual persisted driver wall: `2026.4085628999746` seconds)

Chat explicitly approved this exact plan and the registered Supervisor audited
the one-time extended wall. The Arena/search configuration was unchanged:
training seed 59012, PAIRWISE_RANKING width 32, regularization 1e-3, 600 fit
steps, Arena seed 620700, 2000 nodes/move, depth 12, TT 8 MiB, workers 1,
and `stop_on_decision=false`.

## Final four-pair result

All eight real 9x9 Standard-Shogi games validated under the matching manifest;
the four synthetic smoke games remained excluded. The final game
`game-000003-owner-1.json` completed at 179 plies by checkmate (winner 1).

- Ruleset: `B_CANONICAL_STANDARD_SHOGI`
- Parent checkpoint: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Child checkpoint: `35462d58263581a0f456d863bcd29a78ae82b9d90a82147404bff2346833d1a5`
- Usable training roots: `24`
- Training actions: `157`
- Model SHA256: `eaa1e2c3330c2f5857f16f8dc0f3104de3a765e15b90dc498d36fed86a5c538b`
- Pair scores: `[0.5, 0.0, 0.5, 0.5]`
- Mean pair score: `0.375`
- Child better / tied / child worse pairs: `0 / 3 / 1`
- Game W / D / L: `3 / 0 / 5`
- Directional-failure flag: `true`

The persisted aggregate is
`.generic_chess_flow/f61-gen0-gen1-strength-triage/f61_gen0_gen1_strength_triage.json`.
This is the complete preregistered Standard-Shogi Gen0→Gen1 first-seed result;
no Chess/generated arm, additional seed, Gen2, larger Arena, or historical
teacher-only experiment was started.
