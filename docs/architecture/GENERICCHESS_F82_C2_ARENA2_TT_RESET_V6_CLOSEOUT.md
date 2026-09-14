# F82 C2 Arena2 TT-reset v6 closeout

Date: 2026-09-14  
Mode: Courier  
Sandbox commit: `316a852508b59c0d6a7af85d65fe6ac60ff38133`

## Approved execution

- Run: `f82-c2-arena2-tt-reset-v6-6187cf7fe9f5`
- Plan SHA-256: `7c5895b2fce73db55d00d40a8f1848988e4ca9a5a3002758339b7fcee77b0e83`
- Normalized resource-envelope SHA-256: `7dcc07f4eb596bab0e6ed4fa9fb6fa9e80138ac4c02af971017badd520ede1eb`
- argv digest: `b4aa892aac76ec746459a2ed187b6c477bc86934db6baf53c8f459b6db2933cb`
- Chat response SHA-256: `dce5663f6d40889acee4d72db47d2950f30157b0744a6de0a833074f0db7e0f0`
- Scope: resume only owner-1 pair-0 partial; retain owner-0 terminal; `max_pairs=1` and no pair 1.

The Heavy monitor exited with code 0 after approximately 14m
(`started_at=1789390820.849518`, `finished_at=1789391659.8129773`).

## Pair-0 result

The result artifact `.generic_chess_flow/f82-c2-arena2-tt-reset/arena2_result.json`
(SHA-256 `e1f971b0969d5e66bb07708579ae614354a61b725c8ca251273ec2605988d6`)
reports `status=COMPLETE`, `completed_games=2`, `completed_pairs=1`, and
`total_games=2`.

Role-swapped terminal checkpoints:

- `game-000000-owner-0.json` (SHA-256
  `64069aa8bab79d888e77749579a217007df2c8e0a40d696a588e8db1b6c01c04`):
  380 plies, `checkmate`, winner `1`.
- `game-000000-owner-1.json` (SHA-256
  `fd3c984cd0a4bbf0e4062508511483995ce1a3d66e64eb63c39618b415ee198b`):
  498 plies, terminal `no_contest`, no winner.

This is the first complete symmetric TT-reset pair-0 observation. Pair 1 was
not scheduled and no downstream Arena4/Arena8/final-confirmation or promotion
was attempted. Any decision to enlarge the evidence set remains for Chat's
next work order; this report does not infer a strength conclusion beyond the
observed terminal outcomes.
