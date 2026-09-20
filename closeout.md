# F137 closeout

- Work order: `GENERICCHESS_F137_CORRECTED_SHOGI_NULLSPACE_GAUGE_DECOMPOSITION`
- Baseline: `08f5eb079f6614c834792356ee4d97c1e0786540`
- Scope: corrected Standard Shogi gauge decomposition only; no new states, learner, A2/T1, self-play, MCTS, Arena, or feature changes.
- Heavy runtime: `69.98343706130981` seconds.
- Result artifact: `.generic_chess_flow/f137-shogi-result.json` (ignored transient evidence).

## Reproduction and exact span

- Corrected oracle SHA: `fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6`.
- Feature-name SHA: `6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942`.
- Corpus: 3000/750/750, seed `1220201`, identity `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`.
- F136 reproduction: active `664`, train-constant `422`, design width `665`, rank `652`, nullity `13`.
- Canonical gauge rank `13`, nonzero-spectrum condition number `11.50492792616177`.
- Maximum principal-angle sine `1.9781279289193693e-14`; projector Frobenius difference `5.187307866605657e-14`.
- Canonical gauge reconstruction relative error `6.445899653063839e-15`; holdout prediction difference nRMSE `3.780054084946967e-15`.

## Coverage and residual explanation

- Full material/PST identity held exactly (`0.0` max error) for all 13 types and all splits.
- The reduced active relation is constant on training and breaks outside training exactly with omitted occupancy coverage.
- 33 occupancy/PST coordinates are DEV_COVERED, 37 are HOLDOUT_ONLY, and 352 are never observed outside training.
- Deterministic greedy dev witness set: 19 states covering all 33 DEV_COVERED coordinates.
- Canonical gauge vs corrected F135 residual: Pearson `0.9999999308752232`, residual SSE explained `0.999999861744466`.

## Classification and routing

`CORRECTED_A1_NULLSPACE_EXACTLY_MATERIAL_PST_COVERAGE_GAUGE`

The F136 null space is exactly the material/PST gauge induced by dropping train-constant occupancy cells. Because 37 coordinates are HOLDOUT_ONLY, the next work must generate independent legal training witnesses for those coordinates, plus the 19-state dev witness set where useful; holdout states must remain untouched. F129-F136 semantic conclusions remain quarantined, and corrected A2/T1 remains unauthorized.
