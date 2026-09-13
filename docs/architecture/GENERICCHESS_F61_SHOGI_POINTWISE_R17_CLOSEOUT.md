# F61 Standard-Shogi POINTWISE_Q R17 closeout

Date: 2026-09-14  
Work order: `GENERICCHESS-F61-SHOGI-POINTWISE-CONFIRM-R17`  
Ruleset: `B_CANONICAL_STANDARD_SHOGI`

## Scope and authority

This run kept the R16 POINTWISE_Q child fixed. No learner, optimizer seed,
regularization, roots, scalar calibration, search setting, or checkpoint was
changed. The fixed child was
`78bfa7cad9cc21ecfc95fd166566b25d3c954033b413660a7c398498dd6c571b`, with
model SHA `c6330b17fc11093cd404e204d3a6f461307971f2458e55d0147c4cc21c0f239c`.

Compute was authorized by Chat and the registered Supervisor under plan
`f61-shogi-pointwise-r17-confirm-20260914-v1` (plan SHA
`b4d909e4011a9b4eb1044d89ee461a2857fd987aede72e51e88320408ae14430`) and
resource envelope SHA
`54e6247db9e7929df85655cbc7e84d73d2c2c732912a2f32e75428f77d473bf2`, bound to
sandbox SHA `a8fd7c3535f45ca5712572347e5cf7c340bc2a22`.

## Confirmation protocol

The run used Standard-Shogi at 2,000 nodes/move, depth 12, TT 8 MiB, one
worker, and exactly three fresh role-swapped pairs with opening seed `620707`.
The fresh block produced three separately reportable pair scores:

| pair | score |
| ---: | ---: |
| 0 | 0.5 |
| 1 | 0.5 |
| 2 | 0.5 |

New-block mean: `0.5`; better/tied/worse: `0/3/0`; child game W/D/L:
`3/0/3`. Each pair was one child win and one parent win; all six games ended
by checkmate.

Combining only this block with the preregistered R16 seed-620706 pair `[0.5]`
gives four-pair scores `[0.5, 0.5, 0.5, 0.5]`, mean `0.5`,
better/tied/worse `0/4/0`, and child game W/D/L `4/0/4`.

## Decision

Under the work-order rule (success requires combined mean `> 0.5` and more
better than worse pairs; failure requires mean `< 0.5` and more worse than
better), the fixed POINTWISE_Q child is **inconclusive**. It neither improves
nor degrades playing strength in this four-pair result. Stop here as required:
no new learner, optimizer seed, objective sweep, roots, Chess, generated rules,
or Gen2 was started.

## Reproducibility evidence

- R16 closeout: `GENERICCHESS_F61_SHOGI_POINTWISE_R16_CLOSEOUT.md`.
- R17 command: `.venv\\Scripts\\python.exe scripts/f61_pairwise_scale_calibration.py --training-seed 59013 --objective POINTWISE_Q --run-arena --fresh-arena-seed 620707 --arena-pairs 3`.
- Fixed child checkpoint: `78bfa7cad9cc21ecfc95fd166566b25d3c954033b413660a7c398498dd6c571b`.
- Fresh opening seed: `620707`; R16 seed: `620706`.
- Pointwise fit remained unchanged: RMS ratio `0.9903413792479094`, standard-deviation ratio `0.9908631074058574`, Pearson `0.9985805255107525`, ranking agreement `301/349 = 0.8624641833810889`.

