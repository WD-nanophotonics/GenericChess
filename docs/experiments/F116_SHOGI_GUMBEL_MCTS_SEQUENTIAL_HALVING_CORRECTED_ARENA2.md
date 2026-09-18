# F116 Corrected Shogi Gumbel-MCTS Sequential Halving Arena2

Status: `SHOGI_CORRECTED_GUMBEL_MCTS_POLICY_ITERATION_ARENA2_REJECTED`

F116 corrected the F115 root-budget bug. Non-final rounds now consume only
their reserved base allocation; only the final round spends the residual
budget. The required 64-simulation schedule is 8 candidates × 2, then 4 × 6,
then 2 × 12, retaining 4, 2, and 1 candidate respectively. Per-round
candidate identities, allocations, visits, Q values, survivors, and remaining
budget are persisted, with a regression covering initial candidate counts 2–8.

Frozen inputs:

- value checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- parent policy: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`
- corrected candidate policy: `db29a199d622f0531de94c6b1ffbabcf8845af4945b3a93775889c4c4f01546f`

Genericity and Native/Python parity passed: all three 16-simulation smokes
completed with one survivor, and 100 deterministic Shogi positions matched
with maximum absolute logit error `4.440892098500626e-15`.

Fresh self-play used base seed `1160101` and produced 192 train, 64 dev, and
64 holdout informative roots. Full-batch Adam used 100 steps, learning rate
`0.001`, proximal coefficient `0.001`, and seed `1160111`. Backtracking chose
`alpha=0.5` because alpha 1 failed the dev gate. The parent/candidate CE and
KL metrics were:

| split | parent CE | candidate CE | parent KL | candidate KL |
|---|---:|---:|---:|---:|
| train | 3.291568 | 3.082084 | 1.611522 | 1.402037 |
| dev | 3.223374 | 3.156771 | 1.543327 | 1.476724 |
| holdout | 3.312597 | 3.203958 | 1.632550 | 1.523912 |

The 24-root diagnostic had 0.50 selected-action agreement and mean target KL
57.7225. It is diagnostic only. Complete root and round telemetry is retained
in `.generic_chess_flow/f116-shogi-gumbel-corrected-arena2/report.json`.

Arena2 used fresh openings seed `1160801`, search seeds
`1160901 + 10000*g + p`, two role-swapped pairs, and the 512-ply safety
boundary required by Standard Shogi’s authoritative termination contract. All
four games were valid checkmates at 160, 156, 163, and 353 plies. Pair scores
were `0.5, 0.5`, mean `0.5`, with zero child-better and zero child-worse
pairs. The strength gate therefore rejected the candidate; no promotion is
authorized.

F115’s child and outcomes were not reused. The next diagnosis should remain
within this corrected Gumbel-MCTS loop before changing simulation count,
architecture, value training, or returning to AlphaBeta/TreeStrap.
