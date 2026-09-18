# F115 Shogi Gumbel-MCTS Policy Iteration Arena2

Status: `SHOGI_GUMBEL_MCTS_POLICY_ITERATION_ARENA2_REJECTED`

F115 implemented the generic `SemanticGumbelMCTSV0` tree backend, Native
Policy-v1 logits, a frozen-value offline policy update, and the requested
bounded Arena2 measurement. The backend has no ruleset-name dispatch, no
transposition DAG, and no value learning. Root search uses the required
Gumbel ranking, deterministic sequential-halving allocation, PUCT below the
root, and exactly 64 simulations in production.

Frozen inputs:

- value checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- parent SemanticPolicyV1: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`
- candidate SemanticPolicyV1: `55f4f9da65e1b9dc8f4f63de9b74f0c0067a668f149927a271c630ca11228f31`

Genericity and parity gates passed. Standard Shogi, Western Chess, and the
existing lowered semantic Shogi ruleset all completed 16-simulation uniform
smokes. Native/Python Policy-v1 action order and logits matched on 100
deterministic Shogi positions; maximum absolute logit error was
`4.440892098500626e-15`.

The five-game parent-policy self-play corpus produced 192 train, 64 dev, and
64 holdout informative roots. The warm-start child used full-batch Adam for
100 steps (`learning_rate=0.001`, proximal coefficient `0.001`, seed
`1150111`). Backtracking selected `alpha=1`. Parent to candidate cross-entropy
changed as follows:

| split | parent CE | candidate CE | parent KL | candidate KL |
|---|---:|---:|---:|---:|
| train | 3.205448 | 2.978755 | 1.126006 | 0.899313 |
| dev | 3.203578 | 3.115163 | 1.124137 | 1.035721 |
| holdout | 3.354496 | 3.227135 | 1.275055 | 1.147694 |

The exact 24-root parent/child consistency probe had 0.6667 action
agreement. The complete root corpus and training metrics are retained in the
generated evidence file
`.generic_chess_flow/f115-shogi-gumbel-mcts-arena2/offline-report.json`.

Arena2 used two fresh openings from seed `1150801`, two role-swapped pairs,
game seeds `1150901 + 10000*g + p`, and 64 simulations per nonterminal move.
Three games were valid and ended by checkmate at 151, 206, and 179 plies.
Game 2 reached the hard 256-ply cap while still ongoing, so the arena has
only 3/4 valid games and no strength score is admissible. There were no
invalid actions, search exceptions, or neutral declarations. The persisted
game-level evidence is
`.generic_chess_flow/f115-shogi-gumbel-mcts-arena2/report.json`.

The candidate is therefore not eligible for promotion. The next route remains
diagnosing the Gumbel-MCTS search/termination behavior; this result does not
authorize a return to AlphaBeta or TreeStrap.
