# GenericChess F76-R1 Trusted Pointwise-Q Corrective

## Decision

R1 corrected the F76 fit-corpus contract and produced a valid
`POINTWISE_OUTPUT_DELTA_DEPLOYMENT_VISIBLE` candidate. The original F76
candidate remains preserved as historical evidence and is explicitly invalid
for selection because it was fit on all 48 roots rather than the required
trusted subset.

No Arena, self-play, external-engine comparison, seed sweep, Heavy job, or
promotion was run or authorized by this order.

## Provenance

- Work order: `GENERICCHESS-F76-R1-TRUSTED-POINTWISE-Q-CORRECTIVE`
- Baseline: `b40792426a4df593efb9febe8b97350cc029d097`
- Parent checkpoint: `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`
- Corrected candidate checkpoint: `140daa82ba60d5dee82a9212a679834f3c19919c43bf30704feb51c87fd1c324`
- Durable candidate descriptor: `artifacts/f76_r1_trusted_pointwise_q/candidate.json`
- Preserved invalid F76 checkpoint: `efe6bcf97198a75badae0989720e3a5c05889c0d9f3babbe92c472d686724ffd`
- Invalid-artifact status: `INVALID_FOR_SELECTION_DUE_TO_FIT_CORPUS_CONTRACT_MISMATCH`

R1 used the F62 stage SHA
`e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70` and
records SHA
`b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61`.

## Trusted-root contract

All 48 F62 fit roots were loaded and re-filtered using the original F74
predicate: root-40k and root-80k top action agreement, q10k/q20k top-action
agreement, q10k agreement with deep consensus, and exclusion of both mate-band
conditions. The result was exactly 34 trusted roots with indices:

`[0, 2, 3, 4, 5, 6, 7, 8, 10, 11, 13, 14, 15, 33, 34, 35, 37, 38, 40, 43, 44, 45, 46, 64, 66, 67, 68, 69, 72, 73, 74, 76, 77, 78]`

Only the retained action rows from those 34 roots were used for pointwise
fitting: 246 cached rows. Development data did not participate in fitting or
alpha selection. The high-confidence retention and residual-cap checks used
all 48 fit roots.

## Corrected fit and trust region

The deterministic closed-form 32×32 ridge solve used equal total weight per
trusted root, regularization `0.001`, and
`target = (q20k - base_q - parent_residual) / target_scale`. Only
`output_weights` changed; all representation, checkpoint, ruleset,
perspective, and Native bindings remained frozen.

| Measure | Result |
| --- | ---: |
| Fit roots / trusted roots / rows | `48 / 34 / 246` |
| Raw delta L2 norm | `11.891430165435105` |
| Cosine vs F74 pairwise delta | `0.2355026850318147` |
| Cosine vs invalid F76 delta (diagnostic) | `0.6663577707398769` |
| Objective before / raw delta | `56.328358573158894 / 36.1752100220732` |
| High-confidence boundary | `1.49329745822825` |
| Residual-cap boundary | `5.32011045586063` |
| Applied alpha | `0.7466487291141266` |
| Objective after alpha | `37.46877747685991` |

The high-confidence check covered 12 upper-quartile roots and retained every
Gen1 top action. Parent/candidate maximum fit residuals were
`19,256.2350808158` and `16,213.0090000364`, below the allowed
`38,512.4701616316`. Eight successor-state Native/Python fixed-point delta
checks were exact. Contract and safety failure lists were empty.

## Development diagnostic

Because the corrected direction was below the `0.995` redundancy threshold,
the registered 20-root diagnostic ran with fresh 8 MiB TTs per arm, product
`root_window_pruning=True`, 2,048 nodes, max depth 12, qsearch 0, no root
hint, and one fresh repeat for each parent and child arm.

- Decision changes: `10 / 20`
- Toward deep / away from deep / lateral: `0 / 1 / 9`
- Parent deep agreement / child deep agreement: `2 / 1`
- Fresh-repeat determinism: true
- Completed depths: `80 @ depth 2`
- Aggregate beta cutoffs: `5,362`
- Aggregate TT probes / hits / cutoffs: `159,198 / 7,280 / 0`
- Root-pruning telemetry: true for every search

The raw R1 diagnostic remains ignored under
`.generic_chess_flow/f76-r1-trusted-pointwise-q/f76_r1_results.json`.
