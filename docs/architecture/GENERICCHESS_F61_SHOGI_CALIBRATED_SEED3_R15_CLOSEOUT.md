# F61 Standard-Shogi calibrated optimizer-seed screen — R15 closeout

## Scope and fixed data

R15 screened the third pre-existing optimizer initialization requested by Chat.
It reused exactly the 24 persisted Standard-Shogi roots and 157 q20/base-Q
rows produced under the existing data seed. The learner architecture,
objective, regularization, target/search settings, and scalar method were
unchanged. This is an optimizer-seed screen, not a new data-seed study.

- Ruleset: `B_CANONICAL_STANDARD_SHOGI`
- Parent checkpoint: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Training seed: `59011`
- Training: `PAIRWISE_RANKING`, width 32, regularization `1e-3`, 600 steps
- Persisted roots/actions: `24` / `157`
- Code/report base checkpoint: `dcff775ffd1ca1d1687a739dbbf36753aa63039a`
- Compute plan SHA: `e0432b271ad6b3c438884f2a58f3d2af579f2241a7b79e9b837df3f664938bd4`
- Resource envelope SHA: `c5bf62c66621af1b1db08e2f87b2516953a2c5be4d33f52ba772b391ca48ec87`
- Chat approval request: `GENERICCHESS-20260913-191724-8328bfbb`
- Heavy run: `f61-shogi-seed3-r15-one-pair-b256f17d8a1d`
- Fresh opening seed: `620705`

## Fit and calibration gate

The seed-59011 child checkpoint is
`cf96604562e343ec1ca99a677f5fed76ca7b31133d73299789a580a789c05e12` with
model SHA256
`c538a4fa318afbbe881ac0334396772ce472efc3c529cfb82d59ba0946f3dae3`.

The independently recomputed no-intercept scalar is:

- `alpha = 0.041187666769104674`
- calibrated child checkpoint:
  `eb3acd00eb74a268076301f58527b528b6befd500c037bddf5a44e2dab032368`
- calibrated model SHA256:
  `a31fe98618519e2cf905302540f071cce48e7a3f9ab04775d8e11e00373f69ee`
- actual calibrated prediction versus `alpha * original_prediction` maximum
  absolute error: `1.7053025658242404e-13`
- ranking agreement: `292/349 = 0.836676217765043`

The frozen seed-620700 opening gate used 2,000 nodes, depth 12, and TT 8 MiB.
All four calibrated actions differed from the parent, so the nontriviality
gate passed. The calibrated actions matched the uncalibrated seed-59011 child
on all four openings, as expected for a positive scalar intervention.

## Fresh one-pair screen

The exactly one fresh role-swapped pair ran at opening seed `620705`, with
2,000 nodes/move, depth 12, TT 8 MiB, and one worker. Both games ended in
checkmate:

| game | calibrated-child owner | winner | plies |
|---|---:|---:|---:|
| owner-0 | 0 | 1 (parent) | 186 |
| owner-1 | 1 | 1 (child) | 100 |

The pair score is `[0.5]`, mean `0.5`, with `0` better, `1` tied, and `0`
worse pairs. Game W/D/L from the child perspective is `1/0/1`; directional
failure is false. Under the Chat order's screen rule, the score is `>=0.5`,
so R15 returns before any confirmation expansion. This one pair is not a
strength estimate and should not be pooled with the seed-59012 or seed-59013
checkpoints as if they were one candidate.

## Verification and disposition

The R15 Heavy completed within the approved envelope. No roots were
regenerated, no second alpha or alternative objective was run, and no further
same-design Arena was started. The report is ready for Chat/Supervisor review
at the synchronized sandbox SHA.

