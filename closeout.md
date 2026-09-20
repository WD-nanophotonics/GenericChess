# F136 closeout

- Work order: `GENERICCHESS_F136_CORRECTED_SHOGI_COVERAGE_IDENTIFIABILITY`
- Baseline: `f63eaaffa4c143342fa3d11c05447e8766974a4a`
- Scope: corrected Standard Shogi schema only; no new states, A2/T1, self-play, MCTS, Arena, or representation changes.
- Heavy runtime: `137.3071768283844` seconds.
- Result artifact: `.generic_chess_flow/f136-shogi-result.json` (ignored transient evidence).

## Frozen-input reproduction

- Corrected oracle SHA: `fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6`.
- Feature-name SHA: `6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942`.
- Corpus: 3000/750/750, seed `1220201`, identity `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`.
- F135 PCG holdout: RMSE `211.189237270397`, nRMSE `0.15595845351232307`, R2 `0.9756769607780446`, Pearson `0.9878499297805251`.
- F135 action recovery: top-1 `0.97265625`, pairwise `0.9851308467506316`, normalized regret `0.0024239891704051506`.
- Reproduction passed; exact oracle self-consistency error was zero on all splits.

## Identifiability audit

- Raw features `1086`; active `664`; train-constant `422`.
- Design including intercept: `3000 x 665`; numerical rank `652`; nullity `13`.
- Retained-spectrum condition number `452.41340355195643`; effective ranks at `1e-6`, `1e-8`, `1e-10`: `652`, `652`, `652`.
- 44 train-constant features became variable outside training. Aggregate holdout omitted-constant contribution RMS `0.21583254433560448`, normalized RMS `0.00015938743028420948`; only `0.0017260086491973636` of F135 squared error was explained.
- Matched-ridge plus exact constant correction failed A1: holdout nRMSE `0.1558238023810179`, R2 `0.9757189426115215`.
- Active minimum-norm plus exact constant correction also failed A1: holdout nRMSE `0.15582286152352964`, R2 `0.9757192358266189`.
- Exact active-null holdout contribution: nRMSE `0.15582286152353111`; Pearson with F135 residual after exact constant correction `0.999999930875223`.
- Material/PST dependencies held exactly for every material type and split and were reported separately.

## Classification and routing

`CORRECTED_A1_FAILURE_ACTIVE_SUBSPACE_NONIDENTIFIABILITY_SUPPORTED`

The frozen corpus does not identify active corrected-oracle directions outside its training row space. Constant-feature coverage and ridge bias are not sufficient explanations. The next work should first distinguish globally exact semantic dependencies from corpus-specific active null directions, as directed by F136. F129-F135 semantic conclusions remain quarantined; no promotion or A2/T1 work is authorized.
