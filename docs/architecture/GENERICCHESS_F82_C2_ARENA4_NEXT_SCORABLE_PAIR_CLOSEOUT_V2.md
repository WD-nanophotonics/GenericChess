# GenericChess F82 C2 Arena4 Next Scorable Pair (Opening Index 1) Closeout

Date: 2026-09-15  
Mode: Courier  
Work package: F82 C2 parent-anchored repeatability, Arena4 opening index 1

## Immutable execution binding

- Sandbox commit: `947870be29c68f04785298087828161277cdd2f6`
- Compute plan: `f82-c2-arena4-next-scorable-v2`
- Compute plan SHA-256: `7d318f0ccde8659ca00cf35b2e6665032869ba24e2fc2c19eefb0789f121cd48`
- Resource envelope SHA-256: `e23d3d6f7577e51bc4b5eed1c103869de702e359b94bbf3ec8fdc20cc104f98e`
- Registered Arena4 corpus: `593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1`
- Opening index: `1`
- Seed: `820401`
- Pair contract: one role-swapped pair; 512 nodes/move; depth 12; 8 MiB TT; TT reset each move; two workers
- Effective workload: 2 games, 1 pair, 1024 maximum plies
- Supervisor approval: signed for the exact plan, envelope, and sandbox SHA; transport recovery escalation `e6514ff7688c753e8650` resolved `RESUME_WORKER` before launch

## Result

The approved Heavy invocation completed with status `COMPLETE` and one complete pair:

```text
completed_games=2
completed_pairs=1
game_wins=1
game_losses=1
game_draws=0
mean_pair_score=0.5
opening_final_position_key=fda1ec98b689cdee43b170bdc23ab911446fb6f871d5527afd83fc709b7c0b55
```

| Game | Child owner | Result | Winner | Plies | Final position key | Artifact SHA-256 |
| --- | ---: | --- | ---: | ---: | --- | --- |
| `game-000000-owner-0.json` | 0 | checkmate | 1 | 54 | `3c2098766905dbbe4a65ef3cf2ffc2fc54d1ef5d5a3bc6fc47fb07c8e7c0820e` | `b56cc44b5804b48ab33c33690a32cfbc0b7ba9dd0d0b7597002adb438d0d5b63` |
| `game-000000-owner-1.json` | 1 | checkmate | 1 | 154 | `509592ca0ae4ad06752b561a0a469074a007caf103c34dae1da113b9e805cf44` | `ef9735c2d3749c5781825ec90e9ccb973bbd3013d2195626749863ee2fa67939` |

Result JSON SHA-256: `c34061ab055a6c176993aff50e8cab6454089656d1f993d7907e5e97a3e42619`.

## Aggregate decision

The three valid role-swapped pairs now available in this sequence are:

- Arena2 opening index 1: `0.5`
- Arena4 opening index 0: `0.5`
- Arena4 opening index 1: `0.5`

The aggregate mean is `0.5` across three valid pairs. This remains inconclusive for a strength separation. Per the signed Supervisor boundary and Chat work order, stop further Arena4/Arena8 compute and request mechanism-level reassessment; do not run a fourth pair or promote.

## Verification and publication

The focused regression suite was run before publication:

```text
tests/test_learning_arena_integrity.py
tests/test_f63r1_game_atomic_arena.py
tests/test_f82_c2_parent_anchored_repeatability.py
```

Transient result, progress, plan, and envelope files remain outside Git. This report is the durable closeout artifact; publication and Chat closeout must reference the exact resulting sandbox commit and this report's SHA-256.
