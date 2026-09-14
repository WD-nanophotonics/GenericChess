# F84 bounded native self-play → TDLeaf closeout

This checkpoint follows the revised F84 Courier order. The first composite
plan was held twice; the Supervisor then required two independent small Heavy
decisions with an early learner gate. No composite Heavy or third compute-plan
request was used.

## Published implementation

- Final published sandbox before closeout: `d4d5c27208920e0af944c054ff8f52ebb7edf814`
- Parent checkpoint: `c45623c0b905780ed1fd896a8f9364fd369bed1e641519f45fb40a3faf014d71`
- Candidate checkpoint: `a784a45dc57bf693994ee2315fdf95a99f20ea07bdf27850cca51f1f92482291`
- Candidate descriptor internal SHA: `0932d22bae1f17a3c164cc7763e576bca347c3aa6e6de85ce0f78bed73309a7a`
- Candidate descriptor file SHA: `c5c04e7e2f0cdd9b381bf8f0d41ae628f673e9887e38f4d017603c2ee93f8d59`

The implementation uses the existing `collect_self_play` and `tdleaf_update`
paths. It adds a real `max_plies=64` bound and, for a nonterminal cutoff,
computes a finite frozen-parent bootstrap value. Semantic positions use the
native packed-position dynamic extractor. `TrainingTrajectory.terminal_z`
therefore receives `terminal=ongoing`, `truncated=true`, and an explicit
bootstrap rather than a fabricated draw/zero target.

## Stage A: bounded learner gate

- Envelope: `f84-stage-a-native-selfplay`
- Envelope SHA: `95f02b86d9b53938fce428f4e3927883ee2fee5f03835cc1254f735f9126acf7`
- Stage result SHA: `1ea0d94208039fb14c79da8e4e153c22b48c876f4ccf81d2aca4091d029cab8b`
- One trajectory, 64 plies, 512 nodes/move, depth 12, epsilon 0.10, TT 8 MiB.
- `trajectory_points=64`, `positions_seen=64`
- `trajectory_terminal=ongoing`, `trajectory_truncated=true`
- frozen-parent `bootstrap_value=-0.6354471505664475`
- TDLeaf `weight_l2_delta=0.3539171520327391`, learner changed: true

The gate passed; Stage B was authorized. No second trajectory or second update
was performed.

## Stage B: minimum strength screen

- Envelope: `f84-stage-b-arena4`
- Envelope SHA: `a537d48873086371ea358652f8aa29843b2683382b62d964d1f90a9449499735`
- Registered corpus: `593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1`
- Opening index `0`, seed `820401`, role-swapped one pair, two games,
  512 nodes/move, depth 12, TT reset each move.
- Result JSON SHA: `a33e272fc685994fdd6ce9f76243586bcb1eebcc6f5be086345346eb9d54c732`
- owner 0 (candidate owner 0): parent won by checkmate, 92 plies;
- owner 1 (candidate owner 1): candidate won by checkmate, 92 plies;
- paired score: `0.5` (`game_wins=1`, `game_losses=1`, `draws=0`).

## Decision

The native learning intervention produced a real changed checkpoint with a
proper nonterminal bootstrap, but the immediate role-swapped screen was 1–1.
This is not a positive strength screen and gives no promotion basis. Stop this
candidate after the required pair; do not add another pair, Arena8,
confirmation, sweep, or promotion. Continue the Courier loop for Chat's next
mainline order.
