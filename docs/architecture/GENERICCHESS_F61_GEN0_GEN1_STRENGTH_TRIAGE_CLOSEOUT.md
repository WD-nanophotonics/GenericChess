# F61 Gen0 to Gen1 cross-ruleset strength triage closeout

## Immutable implementation checkpoint

- Sandbox implementation commit: `007fa203902fc30cc8cc304c7b6c43308ca274e6`
- Driver: `scripts/f61_gen0_gen1_strength_triage.py`
- Regression: `tests/test_f61_gen0_gen1_strength_triage.py`
- Work order: `GENERICCHESS-GEN0-GEN1-STRENGTH-TRIAGE`

## Thin experimental path

The driver reuses the existing F59 action-spectrum path, F61 width-32 tanh
residual fit (`PAIRWISE_RANKING`, regularization `1e-3`, 600 steps, seed
`59012`), and equal-budget role-swapped Arena (`2000` nodes/move, depth `12`,
TT `8 MiB`). It parameterizes the same path over Standard Shogi, canonical
Western Chess, and generated fixture `gen_classic_like_4_101`.

The first round is bounded to 24 D0 roots and four Arena pairs per ruleset.
Shogi runs first, Chess second, and generated is opened only when Shogi is not
a directional failure. Mean pair score and child-better versus child-worse
pairs are the real-strength triage signal; teacher/loss/agreement metrics are
diagnostic only. Results remain under `.generic_chess_flow` and are not part of
this checkpoint.

## Verification and compute boundary

The focused driver, plan-boundary, endpoint-rule, and Arena-integrity tests
passed through the publish gate. No training, Arena, Heavy, or R7 216-game
teacher-only computation was run. Any actual execution requires a new compact
Chat work order plus the existing explicit resource/approval gate.
