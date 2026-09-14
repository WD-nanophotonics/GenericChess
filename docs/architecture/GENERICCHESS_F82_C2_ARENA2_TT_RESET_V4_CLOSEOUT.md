# F82 C2 Arena2 TT-reset v4 Heavy closeout

Date: 2026-09-14  
Mode: Courier  
Sandbox commit: `e111ec2186158f97be3de8a3b52a7dde6b0bdf7c`

## Approved resume execution

- Run: `f82-c2-arena2-tt-reset-v4-78960f1292bc`
- Plan SHA-256: `f1841b863541cf5ff0919836439f0e8b923202f2b4c9ce082d589e5a8034d5b4`
- Normalized resource-envelope SHA-256: `3f4e77f2999063d026013ff553db4c5c15e9b02936fb87aafbc3d90bc0f20479`
- argv digest: `b4aa892aac76ec746459a2ed187b6c477bc86934db6baf53c8f459b6db2933cb`
- Chat request: `GENERICCHESS-20260914-115229-c9c39bde` (`COMPUTE_PLAN_APPROVAL=APPROVE`)
- Bound sandbox: `e111ec2186158f97be3de8a3b52a7dde6b0bdf7c`
- Scope: resume the two v3 pair-0 partial prefixes, symmetric TT reset, two lanes, `max_pairs=1`; pair 1 prohibited.

The Heavy monitor exited with code 0 after approximately 22m 20s
(`started_at=1789386928.9631903`, `finished_at=1789388229.1302981`). The run
resumed the saved prefixes; it did not restart from the opening.

## Observed result

The result artifact `.generic_chess_flow/f82-c2-arena2-tt-reset/arena2_result.json`
(SHA-256 `fc6a96e525c83a7837235af422c26c72a45184d760dd1957157c5ed2e233d535`)
reports:

- `status=INCOMPLETE`, `reason=stage_wall_seconds`
- `completed_games=1`, `completed_pairs=0`, `total_games=2`
- `tt_reset_each_move=true`, 512 nodes/move, depth 12, TT 8 MiB

The owner-0 role-swapped game reached a terminal checkpoint:

- `game-000000-owner-0.json`, SHA-256
  `64069aa8bab79d888e77749579a217007df2c8e0a40d696a588e8db1b6c01c04`
- 380 plies/actions; terminal result `checkmate`; winner `1`

The owner-1 role remains resumable and is the only remaining pair-0 work:

- `partial-game-000000-owner-1.json`, SHA-256
  `8a8af8260b760fad5fe2596f9d209db53d484dacd574fbdc429d18d62505a92`
- 371 actions, 189,952 searched nodes, status `partial`

There are no pair-1 files. Because the role-swapped pair is incomplete, this
run supplies no complete C2 strength estimate and does not authorize Arena4,
Arena8, final confirmation, or promotion. The next order should resume the
remaining owner-1 partial under the same immutable parameters.
