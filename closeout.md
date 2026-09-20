# F141 closeout

- Work order: `GENERICCHESS_F141_CORRECTED_SHOGI_KNOWN_ORACLE_T1_COMPRESSION`
- Baseline: `b82e088196b01342352b01bbd1c9599d435532cd`
- Scope: corrected known-oracle one-ply max transform on the frozen F140 root-state representation; no malformed F129 shards, deeper search, self-bootstrap, action-conditioned input, nonlinear layer, or representation changes.
- Corrected oracle SHA: `fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6`.
- Feature-name SHA: `6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942`.
- Heavy runtime: `7327.315267801285` seconds.
- Result artifact: `.generic_chess_flow/f141-corrected-shogi-result.json` (ignored transient evidence).

## F140 reproduction and fresh T1 shards

- Reproduced active features `773`, design width `774`, numerical rank `761`, nullity `13`, train `3109`, dev `731`, holdout `750`.
- Reproduced direct holdout RMSE `0.371665296350058`, nRMSE `0.0002744663771323697`, R² `0.9999999246682079`, Pearson `0.9999999633278593`, action top-1 `0.97265625`, pairwise `0.988520006832259`, normalized regret `0.0024239891704051506`.
- Holdout identity and bytes were preserved: `7b28486ff7e778ad999eaa6c9df8c430a925a0ca22e730add4147821e32f943e`.
- Created `F141_CORRECTED_T1_LABEL_SHARD_V1` with shard size `128`: `37` shards, `4590` roots, and `200747` action rows.
- Child evaluation cache contained `200678` unique child identities with `69` duplicate-child reuses. Immediate terminal children: `199`; root/child declaration diagnostics: `0`/`0`.
- Legal-action distribution: mean `43.735729847494554`, median `37`, p90 `76`, p95 `90`, max `185`.
- Every shard passed schema, root-count, and root-sequence integrity checks. T1 is exactly `max_a(-V_corrected*(child))` with lexicographically smallest action identity as the stable tie-break; terminal/declaration information was diagnostic only.

## T1 compression and controls

- PCG/matched-ridge numerical gate passed: finite parameters, relative residual `9.391466242135323e-13`, objective excess `-8.326672684626674e-17`, PCG-vs-ridge holdout nRMSE `2.6913282318770637e-10`.
- T1 holdout fit failed the corrected representation gate: RMSE `2769.269142472943`, nRMSE `1.8302864928571427`, R² `-2.3499486459352967`, Pearson `0.45311550928419064`, Spearman `0.33033990104871297`.
- Static root V* baseline holdout RMSE `1544.504502406404`, nRMSE `1.0208057012425626`, R² `-0.04204427968932012`, Pearson `0.8224944589418391`; compressed T1 relative RMSE reduction `-0.7929822400376969`, so usefulness also failed.
- F140 learned-teacher shadow remained stable on holdout: exact-vs-learned teacher top-1 `0.984`, pairwise action ordering `0.9729629736752038`, mean corrected-oracle regret `0.3439474074000027`, normalized regret below `0.01`.
- Search diagnostic retained 64 roots, top-action/PV-head agreement `0.8125`, depth parity `0.96875`, node parity `1.0`.
- Holdout T1 displacement from root V*: RMS `1544.504502406404`, mean absolute `1277.8445138897112`, Pearson `0.8224944589418391`, Spearman `0.6951846385504685`; teacher top-2 gap mean `388.4915296303866`, median `100.89444444500003`.

## Classification and routing

`CORRECTED_STATIC_BASIS_NOT_CLOSED_UNDER_ONE_PLY_MAX`

The numerical solver is sound, but the unchanged linear corrected root-state basis is not sufficiently closed under the exact one-ply max transform. This is a narrow representation-closure result and does not generalize to nonlinear, action-conditioned, or successor-state models. F129-F134 malformed-oracle conclusions remain quarantined; F135-F140 corrected-oracle evidence remains valid. The next controlled step should use the same fresh corrected action spectra for an action-conditioned factorization before arbitrary feature expansion.
