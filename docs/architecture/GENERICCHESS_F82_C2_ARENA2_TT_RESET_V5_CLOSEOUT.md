# F82 C2 Arena2 TT-reset v5 Heavy closeout

Date: 2026-09-14  
Mode: Courier  
Sandbox commit: `c2a11132799c218ffb0ec60d2dbcb0aed4746e10`

## Approved tail-resume execution

- Run: `f82-c2-arena2-tt-reset-v5-2373308dac36`
- Plan SHA-256: `ce27bd7c1785161bde4a9688863d948e563e38c0a3a6976fee1ebe3d87f8120b`
- Normalized resource-envelope SHA-256: `e03c747a7703ac8eabe7bb86bd3d2e7f6b40ba4c823c221a4a899abffc7019d7`
- argv digest: `b4aa892aac76ec746459a2ed187b6c477bc86934db6baf53c8f459b6db2933cb`
- Chat normal response SHA-256: `6f924b879acc00e5e11ce8c94fa69ff914d9b0376175d0cf369c38fcd2d339cb`
- Bound sandbox: `c2a11132799c218ffb0ec60d2dbcb0aed4746e10`
- Scope: resume only owner-1 pair-0 partial; retain owner-0 terminal; `max_pairs=1` and no pair 1.

The Heavy monitor exited with code 0 after approximately 5m 52s
(`started_at=1789389721.749766`, `finished_at=1789390073.8042948`).

## Observed result

The result artifact `.generic_chess_flow/f82-c2-arena2-tt-reset/arena2_result.json`
(SHA-256 `fc6a96e525c83a7837235af422c26c72a45184d760dd1957157c5ed2e233d535`)
reports `status=INCOMPLETE`, `reason=stage_wall_seconds`,
`completed_games=1`, `completed_pairs=0`, and `total_games=2`.

The retained owner-0 terminal checkpoint is unchanged: 380 plies,
`checkmate`, winner `1` (`game-000000-owner-0.json`). The only remaining
work is owner 1, whose resumable partial advanced to 410 actions/410 plies and
209,920 searched nodes (`partial-game-000000-owner-1.json`, SHA-256
`de9ac755466c245c0c1ac35a90a551598d4bde5ce2d6d39ea3ae0760410f295e`).

No pair-1 files were created. A complete role-swapped pair and any C2
strength conclusion are therefore still unavailable; do not enter Arena4,
Arena8, final confirmation, or promotion. The next order should continue this
same owner-1 partial without restarting owner 0.
