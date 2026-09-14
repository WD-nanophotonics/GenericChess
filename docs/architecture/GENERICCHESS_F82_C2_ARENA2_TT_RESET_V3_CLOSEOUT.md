# F82 C2 Arena2 TT-reset v3 Heavy closeout

Date: 2026-09-14  
Mode: Courier  
Sandbox commit: `8753c5625fe942fc2d163bce37b2795f533d6918`

## Approved execution

- Run: `f82-c2-arena2-tt-reset-v3-3343bd6a7b5b`
- Plan SHA-256: `17dc44647dfa752826c0eff2706a10b76776e7ea40b5ca583640168657e9f19b`
- Resource-envelope SHA-256: `895432363c236a6665989721c74031b7a14103aeceadc8f35df7c12f0046f514`
- argv digest: `b4aa892aac76ec746459a2ed187b6c477bc86934db6baf53c8f459b6db2933cb`
- Approved scope: fresh TT-reset Arena2, two concurrent lanes, `max_pairs=1`; pair 1 prohibited.

The Heavy monitor completed with exit code 0. It ran from epoch `1789385652.5733285` through `1789386384.4948509` (approximately 12m 12s). The result artifact is
`.generic_chess_flow/f82-c2-arena2-tt-reset/arena2_result.json` (SHA-256
`7ec74beae816644aa796c1a13fe0ae2316edd6d28f25197e95e5d33f07b37e2b`).

## Observed result

The artifact reports:

- `status=INCOMPLETE`
- `reason=stage_wall_seconds`
- `completed_games=0`, `completed_pairs=0`, `total_games=2`
- `tt_reset_each_move=true`, two workers, 512 nodes per move, depth 12

Both permitted pair-0 roles wrote resumable partials at the terminal timestamp;
there are no `game-*` terminal files and no pair-1 files. The partial evidence
is retained outside Git:

- `partial-game-000000-owner-0.json`, SHA-256
  `18fedc4bbbbc9dd859b487e6755de24aa0b0af7009547967a31d453888084060`
- `partial-game-000000-owner-1.json`, SHA-256
  `b3d30f4f293cfb6b4713f9b95fe4bf73ea9ea743fd5f6ae3726ab23ad2838d2d`

The run therefore provides resumable protocol evidence only. It does not
provide a completed game, pair, strength estimate, or promotion evidence.
No pair-1 launch occurred, satisfying the v3 scheduler boundary.

## Verification and next action

The scheduler correction and focused F82/F63 regressions were already tested at
the bound sandbox SHA (`19 passed`). This closeout records the Heavy result;
generated runtime state and raw output remain ignored. Chat must decide the
next work order before any further Heavy request is prepared.
