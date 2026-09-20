# F138 closeout

- Work order: `GENERICCHESS_F138_CORRECTED_SHOGI_TARGETED_GAUGE_COVERAGE_A1`
- Baseline: `50e02a9be7042b4c89a5313740f78a2165831124`
- Scope: targeted corrected Standard Shogi coverage repair and A1 only; no A2/T1, self-play, MCTS, Arena, or feature changes.
- Heavy runtime: `2171.8805997371674` seconds.
- Result artifact: `.generic_chess_flow/f138-shogi-result.json` (ignored transient evidence).

## Coverage repair

- Corrected oracle SHA: `fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6`.
- Feature-name SHA: `6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942`.
- Corpus: 3000/750/750, seed `1220201`, identity `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`.
- F137 reproduction: DEV_COVERED `33`, HOLDOUT_ONLY `37`, NEVER_OBSERVED_OUTSIDE_TRAIN `352`, dev witness count `19`, gauge rank `13`.
- Transferred exactly 19 original dev witnesses; augmented dev has `731` states.
- Independent generator seed `1380201`, trajectory cycle `(8, 24, 64, 128, 192, 256)`.
- Generated `6125` candidate witnesses after inspecting `37066` legal ongoing states across `342` trajectories; deterministic greedy minimization selected `25` witnesses covering `37/37` targets.
- Augmented surfaces: train `3044` (`3000 + 19 + 25`), dev `731`, untouched holdout `750`.
- No original holdout identity entered training; generation used no holdout states, trajectories, oracle values, or labels.

## Identifiability and fit

- Augmented design: active `773`, train-constant `313`, width `774`, rank `696`, nullity `78` (required nullity was `13`).
- Canonical material/PST gauge activation on holdout was zero within numerical tolerance for every type.
- The canonical gauge span did not equal the full numerical null space: span projector difference `8.062257748298443`, maximum principal-angle sine `1.0000000000000009`, and the exact-span gate failed.
- Numerical solver gate passed: relative residual `8.950983970759459e-13`, objective excess `1.0587911840678754e-22`, PCG-vs-matched holdout nRMSE `4.676203073796356e-10`.
- Holdout scalar result: RMSE `194.3491865316513`, nRMSE `0.14352245864710567`, R2 `0.9794013038638898`, Pearson `0.9896508133242284`, Spearman `0.9505162213621713`.
- Improvement over F135: nRMSE `0.15595845351232307` to `0.14352245864710567`; RMSE `211.189237270397` to `194.3491865316513`.
- One-ply action gate passed: top-1 `0.97265625`, pairwise `0.9853016532268939`, normalized regret `0.0024239891704051506`.

## Classification and routing

`F138_GAUGE_COVERAGE_REPAIR_INCOMPLETE`

The 37 targeted coordinates were covered, but additional corpus-specific null relations remain beyond the 13 canonical material/PST gauges. Stop scientific interpretation here; the next order must diagnose those relations before any further corpus expansion or A2/T1 work. F129-F137 semantic conclusions remain quarantined, and corrected A2/T1 remains unauthorized.
