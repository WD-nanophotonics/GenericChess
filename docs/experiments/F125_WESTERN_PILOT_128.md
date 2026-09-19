# F125 Western Chess expansion (128 decision roots)

This independently retained expansion follows the 64-root Western pilot,
which was insufficient only because it had fewer than 32 informative roots.
The scientific calculations and gates are unchanged.

## Provenance

- Work order: `GENERICCHESS-20260918-190003-5ff9ae6d`
- Implementation SHA: `a9d224fbae03dba42a067ca2d93c578a30551b2d`
- Baseline: `23a0b78ad7f67dbe14186ea98f68c1698e3df395`
- Heavy run: `f125-western-128-v1-0367eb8d1cf6`
- Argv digest: `b9d100fb8d7c20f692e92b7a077bf6d62feb5150c2cc9a62eb9a5c7850119874`
- Resource envelope: 45-minute expected / 60-minute hard wall; 128 roots
- Raw result SHA256: `386d84e5a5b601b84cf4739fe4484b64503fcdb4282576c8f10241a1277e25e6`
- Runtime: `1748.9025464057922` seconds; exit code `0`

## Frozen inputs and exclusions

- Ruleset: `western_chess`
- Oracle-weight SHA256:
  `77cfc280d9108a461629e9de492b71d8257213fc8088ce69c1584232c2668ec9`
- Retained F122 corpus SHA256:
  `79625a972c980c607eb6a9a1b930ebaba2fd447bbe320c52b3ec62ae510b91ac`
- Corpus: 4,500 rows; 4,437 retained; 63 terminal-tactical exclusions.
- Decision seed: `1250121`; 128 generated and 128 retained roots.

## Gates and classification

Direct control passed: PCG residual `8.700717508891171e-11`, holdout
normalized RMSE `0.03142727561375219`, R2 `0.9990123263474973`, and Pearson
`0.9995277249082504`.

Search-target numerical agreement passed. The representation gate did not
pass: holdout normalized RMSE `0.4146912182164913`, R2
`0.8280311935391224`, and Pearson `0.910905304770128`.

The 128-root decision corpus had 52 informative roots, clearing the required
32. Static teacher agreement was `0.59375`; compressed top-1 agreement was
`0.40625`, pairwise agreement `0.5878025583047825`, mean normalized teacher
regret `0.002347176800136381`, disagreement recovery
`0.1346153846153846`, and correct-retention `0.5921052631578947`.

Classification: `HANDCRAFTED_BASIS_T1_SEARCH_TARGET_COMPRESSION_LIMIT_SUPPORTED`.
