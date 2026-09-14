# F83 C3 first teacher-disagreed antecedent closeout

This checkpoint follows the imported Courier order to make the smallest real
learner change at the first frozen teacher-disagreed successor antecedent and
immediately run the minimum strength probe.

## Learner change

- Published sandbox: `b47b4bc645a81b515eaff995ca7d022826bf47b3`
- Work order: `GENERICCHESS-F83-C3-FIRST-TEACHER-DISAGREED-ANTECEDENT`
- Antecedent: `c1_on_policy-a-01`
- Parent checkpoint: `86f026ef85d60e600bc1bd6bc7b7285f11e5ce7e6528911b2ea361a489dc5983`
- Successor checkpoint: `c45623c0b905780ed1fd896a8f9364fd369bed1e641519f45fb40a3faf014d71`
- Successor model SHA: `86f1a9ded05e8d6b8a08b20cf4e97d5c9914fa4026fb7e170247ac7881ac61f7`
- Descriptor SHA: `57ffbd4ac8c72675f51919e013a7fcb96cc511356ca329fa3f05b297e8cd92fc`
- The parent top action was the rook move; the successor top action is the
  frozen deep-teacher knight target. The descriptor test records this actual
  learner behavior change.

Targeted tests passed (`3 passed`):
`tests/test_f83_c3_first_antecedent_successor.py` and
`tests/test_f83_c2_selective_successor.py`.

## Minimum approved strength probe

- Plan: `f83-c3-first-antecedent-arena4-v1`
- Plan SHA: `c42d38518377672b5b8e1e2af422a0c7f726d974df7543b9ea61495f405c3f64`
- Envelope SHA: `d481e0f624b5d252ad411d84d115dce5f5e00b80ff7f07f9615b7b668e29d025`
- Plan sandbox binding: `b47b4bc645a81b515eaff995ca7d022826bf47b3`
- Registered corpus: `593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1`
- Opening index: `0`, seed `820401`
- Pair: one role-swapped pair, two games, 512 nodes/move, depth 12, 8 MiB TT,
  TT reset each move, two concurrent lanes.
- Chat scientific approval: `GENERICCHESS_COMPUTE_PLAN_APPROVAL=APPROVE`.
- Supervisor approval was bound to the exact plan, envelope, and sandbox SHA.

The first Heavy invocation left both games partial and returned `INCOMPLETE`;
the exact command was resumed using the retained game-level progress. The
resumed run completed the planned pair:

- owner 0 (candidate as owner 0): parent won by checkmate, 84 plies;
- owner 1 (candidate as owner 1): candidate won by checkmate, 92 plies;
- paired score: `0.5` (`game_wins=1`, `game_losses=1`, `draws=0`).

Result JSON SHA256:
`f00b34f3452aedf78fd4dd2305bb31a4429d139623c51bf416aaefaa052e1a4`.

## Decision

The antecedent correction demonstrably changes the learner and preserves the
bounded one-pair harness, but the immediate role-swapped strength probe is
neutral (1–1). This is not evidence of strength improvement and provides no
promotion basis. Stop this successor branch at the required minimum probe;
do not add another pair, Arena8, or promotion in this order. Continue the
Courier loop for Chat's next scientific instruction.
