# F140 closeout

- Work order: `GENERICCHESS_F140_CORRECTED_SHOGI_RANK_TARGETED_GENERATION_A1`
- Baseline: `c0a0bf38dbeaa1d0b196b59fe649c91fd39f2132`
- Scope: targeted corrected-Shogi rank completion from the frozen F138/F139 surface only; no A2/T1, self-play, MCTS, Arena, or representation changes.
- Heavy runtime: `4126.90951752663` seconds.
- Result artifact: `.generic_chess_flow/f140-shogi-result.json` (ignored transient evidence).

## Frozen-pool reproduction and targeted generation

- Corrected oracle SHA: `fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6`.
- Feature-name SHA: `6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942`.
- Corpus: 3000/750/750, seed `1220201`, identity `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`.
- Exact F139 reproduction: F138 train `3044`, candidate pool `6125`, F138 rank `696`, nullity `78`, no-new-active candidates `2096`, attainable rank `751`, attainable nullity `23`.
- Dimension identity: existing pool gain `55`, target gain `65`, targeted gain `10`.
- Continuation started at trajectory `342`; searched `1128` trajectories and inspected `123263` legal ongoing states.
- Accepted exactly `10` no-new-active rank-increasing witnesses, reaching rank `761`; no oracle was used before acceptance.

## Rank-complete identifiability

- Final surface: train `3109`, dev `731`, holdout `750`; all surfaces unique and disjoint.
- Active features `773`; train-constant features `313`; design width `774`; numerical rank `761`; nullity `13`.
- Canonical gauge span equals the full numerical null space: principal-angle sine `1.5586792777959428e-14`, projector difference `4.7867056801141723e-14`.
- All 13 holdout gauge activations are zero; exact oracle-null holdout nRMSE `6.638373174350063e-15`, max absolute oracle-unit difference `3.35904779888642e-11`.
- Holdout identity and bytes were preserved: `7b28486ff7e778ad999eaa6c9df8c430a925a0ca22e730add4147821e32f943e`.

## Recovery controls

- Minimum-norm numerical fit passed: relative residual `9.3339531880011e-13`; holdout prediction-difference normalized RMSE `1.8562793115344716e-10`.
- Scalar holdout: nRMSE `0.0002744663771323697`, RMSE `0.371665296350058`, R² `0.9999999246682079`, Pearson `0.9999999633278593`; scalar A1 gate passed.
- Action recovery gate passed: top-1 agreement `0.97265625`, pairwise ordering agreement `0.988520006832259`, mean normalized regret `0.0024239891704051506`.
- Search diagnostic: top-action agreement `0.8125`, PV-head agreement `0.8125`, depth parity `0.96875`, node parity `1.0`, 64 roots.
- Provenance gates passed: holdout identity absent from training; selection used only features, masks, constants, normalization, and rank; no oracle before acceptance.

## Classification and routing

`CORRECTED_KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES_ON_RANK_COMPLETE_SURFACE`

The corrected Shogi surface now reaches the requested rank-complete identifiability target while preserving the holdout and passing scalar, action, numerical-control, and provenance gates. F129-F139 semantic conclusions remain quarantined; no A2/T1 or representation work is authorized by this phase.
