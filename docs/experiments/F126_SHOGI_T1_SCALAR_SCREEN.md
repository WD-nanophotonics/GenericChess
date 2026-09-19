# F126 Standard Shogi T1 Scalar Compression Screen

## Scope and decision

This experiment implements `GENERICCHESS_F126_SHOGI_T1_SCALAR_COMPRESSION_SCREEN`
from baseline sandbox commit `33b78ffde70f2841a034e80e496f13d7806a4a12`.
It is a Standard Shogi-only deterministic subset screen. It does not run
Western Chess, depth-2 roots, self-play, MCTS, Arena, or an automatic F127
follow-up.

The final classification is:

`F126_SHOGI_SUBSET_DIRECT_CONTROL_INSUFFICIENT`

The direct scalar control did not satisfy every pre-registered numerical gate,
so the work order correctly stopped before generating T1 labels or fitting the
search-compressed representation.

## Reproducibility

- Oracle SHA256: `dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316`
- Full ordered F122 corpus identity SHA256:
  `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`
- Full corpus: 4,500 ordered identities, seed `1220201`
- Selection rule: ordinal `floor(j*N/K)`, independently of labels
- Selected identity SHA256:
  - train: `65b0ac8c842ee8eb4164926797782b5469704285c9fd3d0b8e97bf78ad1076b3`
  - dev: `91929864cab22ba1fc065f9acdc49855751a9761ebd28b9cda76202fe01e6e63`
  - holdout: `0173ba68eed4c779322214b3ef6c819726cb5476703214d00e4d8255a7b580b3`

The first bounded Heavy attempt (`f126-shogi-t1-v1-b4ad1be3a79c`) reached the
direct-control reporting stage but exited only because the report serializer
treated metadata strings as metric mappings. After that ordinary technical
failure was fixed, the same bounded work order was rerun as
`f126-shogi-t1-v2-a79eb340c024` with the same resource envelope and argv
digest `b1638f1aeb2adcaa047f67a1bc489edcdcb34808a73d6fe15b7c61645f7d7384`.
The valid run exited 0 in 963.8268 seconds. Its ignored raw result artifact
has SHA256
`7EA1F7FA4A3301BFC8F78CB1B33EFAAE16B61D1FB96E350F2A51722D2980A0E0`.

## Exclusions and retained rows

The benchmark helper builds each root's children once and reuses those child
states for T1 features, spectrum action/value features, terminal detection,
and Shogi declaration checks. The primary fit excludes terminal children,
root declarations, and immediate-child declarations.

| split | selected | terminal child | root declaration | child declaration | retained |
|---|---:|---:|---:|---:|---:|
| train | 1024 | 29 | 0 | 0 | 995 |
| dev | 256 | 4 | 0 | 0 | 252 |
| holdout | 256 | 2 | 0 | 0 | 254 |
| total | 1536 | 35 | 0 | 0 | 1501 |

## Direct-control result

The gate thresholds were: relative residual <= 1e-10, objective excess versus
matched ridge <= 1e-10, normalized PCG-vs-ridge holdout difference <= 1e-8,
holdout nRMSE <= 0.05, R2 >= 0.99, and Pearson >= 0.995.

The following checks passed: relative residual, objective excess, holdout R2,
and holdout Pearson. The following checks failed: PCG-vs-ridge prediction
difference and holdout normalized RMSE.

PCG holdout metrics:

- RMSE in oracle units: `231.87454453698209`
- normalized RMSE: `0.05374232373314101`
- R2: `0.9971117626397623`
- Pearson: `0.9985856113543018`
- Spearman: `0.996898725255251`
- nonzero sign agreement: `0.9881889763779528`
- maximum absolute error: `659.0728599491003`
- relative linear-system residual: `9.124497750611546e-11`
- objective excess versus matched ridge: `5.974229256102987e-19`
- holdout PCG-vs-ridge difference: `6.981889999320072e-05` oracle units,
  normalized `1.6182155456602698e-08`

Because the direct control was insufficient under the specified strict gates,
no T1-label stage, search-compressed fit, or representation classification was
run. The implementation and the child-state reuse regression are covered by
the focused F125 test suite: 6 passed; Python bytecode compilation also
passed.
