# F125 Western Chess pilot (64 decision roots)

This is the independently retained Western Chess stage of F125. The pilot
uses the F125 one-ply known-oracle target, exact F124 PCG objective, depth-2
teacher, and existing gates. It is a decision-corpus pilot only; it does not
change production search or evaluator code.

## Provenance

- Work order: `GENERICCHESS-20260918-190003-5ff9ae6d`
- Implementation SHA: `a9d224fbae03dba42a067ca2d93c578a30551b2d`
- Baseline: `23a0b78ad7f67dbe14186ea98f68c1698e3df395`
- Heavy run: `f125-western-pilot-v2-6215cdd7a8a0`
- Argv digest: `6d17ba8227ae8a0f8fe170a16850dd7ac78df5321064ccf59b1761285fb40789`
- Resource envelope: 45-minute expected / 60-minute hard wall; one family;
  64 requested roots
- Raw result SHA256: `6e7a0f8e5d7add3d838732faa1d599919102bf3c59418de8f1d4360a820d1cf8`
- Runtime: `1286.7525429725647` seconds; exit code `0`

## Frozen inputs and exclusions

- Ruleset: `western_chess`
- Oracle-weight SHA256:
  `77cfc280d9108a461629e9de492b71d8257213fc8088ce69c1584232c2668ec9`
- Retained F122 corpus SHA256:
  `79625a972c980c607eb6a9a1b930ebaba2fd447bbe320c52b3ec62ae510b91ac`
- Corpus: 4,500 rows; 4,437 retained; 63 terminal-tactical exclusions.
- Decision seed: `1250121`; 64 generated and 64 retained roots.

## Gates and classification

Direct control passed: PCG residual `8.700717508891171e-11`, holdout
normalized RMSE `0.03142727561375219`, R2 `0.9990123263474973`, and Pearson
`0.9995277249082504`.

Search-target numerical agreement passed. The representation metrics were
holdout normalized RMSE `0.4146912182164913`, R2 `0.8280311935391224`, and
Pearson `0.910905304770128`, so the representation gate did not pass.

The decision corpus had 22 informative roots, below the required 32. Static
teacher agreement was `0.65625`; compressed top-1 agreement was `0.390625`,
pairwise agreement `0.5987679215049251`, disagreement recovery
`0.13636363636363635`, and correct-retention `0.5238095238095238`.

Classification: `F125_T1_TEACHER_INSUFFICIENTLY_INFORMATIVE`.

Because the pilot was specifically insufficient on informative-root count,
the next lawful Western stage is the smallest expansion, 128 decision roots.
