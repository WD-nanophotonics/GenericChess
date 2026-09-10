# GenericChess F76 Parent-Retained Pointwise-Q Output Delta

## Decision

F76 produced an independent output-layer-only pointwise-Q correction and
classified it as `POINTWISE_OUTPUT_DELTA_DEPLOYMENT_VISIBLE`. The candidate
changed eight of the 20 stable development decisions under the registered
2,048-node product search. All eight changes were lateral; none moved toward
or away from the cached deep consensus.

This order did not authorize Arena, self-play, external-engine comparison,
seed sweeps, Heavy, or promotion. A later order must decide any strength
measurement.

## Frozen data and candidate

- Work order: `GENERICCHESS-F76-PARENT-RETAINED-POINTWISE-Q-OUTPUT-DELTA`
- Baseline: `e680f6ab09b15cc13520d8655b7100a1540b8134`
- Parent checkpoint: `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`
- Candidate checkpoint: `efe6bcf97198a75badae0989720e3a5c05889c0d9f3babbe92c472d686724ffd`
- Durable candidate descriptor: `artifacts/f76_parent_retained_pointwise_q/candidate.json`
- F62 stage SHA: `e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70`
- F62 records SHA: `b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61`

The Gen1 input normalization, hidden weights/bias, target scale, output bias,
hand binding, perspective, Native scale, and all board/hand/dynamic/spatial/
control weights remained frozen. Only the 32 output weights changed. The
candidate model SHA is
`13de777a94f866e1ea6cfb9420babbfc7877c1919d80b83adf16180eddd55b33`.

## Pointwise fit and trust region

The fit used all 48 F62 fit roots and all cached action rows, with equal total
weight per root, ridge regularization `0.001`, and a deterministic closed-form
32×32 linear solve. Each target was
`(q20k - base_q - parent_residual) / target_scale`.

| Measure | Result |
| --- | ---: |
| Fit roots / cached action rows | `48 / 246` |
| Raw delta L2 norm | `16.403981146911892` |
| F74 raw-delta cosine | `0.025230643712375742` |
| Objective before | `78.43905484019479` |
| Objective after raw delta | `50.260435787259` |
| High-confidence boundary | `1.1388156215435` |
| Residual-cap boundary | `3.22737886066671` |
| Applied alpha | `0.5694078107717522` |
| Objective after alpha | `55.4850232162691` |

The upper-quartile static-margin check covered 12 fit roots and retained the
Gen1 top action on all of them. Across all 48 fit roots, parent maximum
absolute residual was `19,256.2350808158`; candidate maximum was
`16,135.663477526`, below the allowed `38,512.4701616316`. The eight sampled
successor states used for Native/Python parity were exact, and all contract
failures were empty.

Because the cosine was below the `0.995` redundancy threshold, the registered
20-root diagnostic ran. It used fresh parent and child engines/8 MiB TTs per
arm, product `root_window_pruning=True`, max depth 12, qsearch 0, and no root
hint. Each parent and child arm was repeated once.

## Development diagnostic

- Decision changes: `8 / 20`
- Toward deep / away from deep / lateral: `0 / 0 / 8`
- Parent deep agreement / child deep agreement: `2 / 2`
- Fresh-repeat determinism: true
- Completed-depth distribution: `80 @ depth 2`
- Aggregate beta cutoffs: `5,258`
- Aggregate TT probes / hits / cutoffs: `159,204 / 7,472 / 0`
- Root-pruning telemetry: true for every search

The raw diagnostic result remains ignored under
`.generic_chess_flow/f76-parent-retained-pointwise-q/f76_results.json`.
