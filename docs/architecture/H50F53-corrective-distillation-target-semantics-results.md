# H50 F53 corrective distillation-target semantics

Status: completed on 2026-09-04. Parent checkpoint: `2127bdfe54dff20dc37b4aadad6151a3a372afd5`. This corrective preserves the accepted F53 variance measurement and changes only the target-comparison semantics.

## Corrections

The deep-search label now uses the checkpoint's explicit `semantic_native_scale` contract (`256` for the v2 dynamic evaluator), converts the Native side-to-move score into owner-0 perspective, and only then applies the learning normalization:

```text
owner0_score = (native_score / semantic_native_scale)
               * (+1 if side_to_move == 0 else -1)
target = tanh(owner0_score / value_scale)
```

The implementation also compares TDLeaf(lambda), terminal-return Monte Carlo, and deep-search distillation on exactly the same four deterministic labeled points per trajectory. No unlabeled point is silently substituted with a terminal-return target. A focused regression verifies that Native score `256` maps to one value unit and that the owner-1-to-move witness is the sign inverse of the owner-0 witness.

## Protocol

The rerun used four independent batches of eight trajectories per ruleset, the existing 400-node trajectory budget, 4,000-node deep-search labels, the fixed validation slices `S49-M[32:48]` and `S49-M[48:64]`, stable 80k current-v2 teacher surfaces, and the common `0.0005` (0.05%) full-parent-L2 diagnostic magnitude. Each batch contained 32 deep labels; each target direction used those same 32 points.

## Corrected labels and target geometry

Across all batches, corrected deep labels were Western `[-0.2741, 0.5487]` and Shogi `[-0.8250, 0.0984]`, rather than fixed-point-saturated values. Target directions remain close but are no longer identical to the prior hybrid measurement:

| Ruleset | TD vs MC | TD vs deep distill | MC vs deep distill | Largest unit distance |
| --- | ---: | ---: | ---: | ---: |
| Western | 0.999518 | 0.999998 | 0.999574 | 0.03104 |
| Shogi | 0.999472 | 0.999894 | 0.999838 | 0.03249 |

The accepted batch-variance result remains unchanged: full-vector TD directions were highly reproducible, with pairwise cosines Western `0.999410–0.999862` and Shogi `0.999936–0.999980`.

## Validation comparison

All values below use the same common diagnostic magnitude. `agreement` is candidate agreement with the 80k teacher; `parent` is the parent agreement on the same slice.

| Ruleset | Target | Native-effective | `[32:48]` agreement / parent | `[48:64]` agreement / parent | Flip rate `[32:48]` / `[48:64]` |
| --- | --- | ---: | ---: | ---: | ---: |
| Western | TDLeaf(lambda) | 3 | 0.3750 / 0.4375 | 0.3125 / 0.3125 | 0.1250 / 0.0625 |
| Western | Monte Carlo | 4 | 0.3750 / 0.4375 | 0.3125 / 0.3125 | 0.1250 / 0.0625 |
| Western | Deep distill | 3 | 0.3750 / 0.4375 | 0.3125 / 0.3125 | 0.1250 / 0.0625 |
| Shogi | TDLeaf(lambda) | 5 | 0.2500 / 0.4375 | 0.1250 / 0.6250 | 0.6875 / 0.8125 |
| Shogi | Monte Carlo | 7 | 0.2500 / 0.4375 | 0.1250 / 0.6250 | 0.6875 / 0.8125 |
| Shogi | Deep distill | 5 | 0.2500 / 0.4375 | 0.1250 / 0.6250 | 0.6875 / 0.8125 |

Teacher stability from 40k to 80k was Western `0.9375` and `0.8750` on the two slices, and Shogi `1.0` on both. No corrected target improved teacher agreement over parent on either held-out slice, so no distillation child or 8-pair arena was authorized.

## Conclusion

The corrective resolves the three implementation defects and invalidates the prior hybrid-target interpretation. After correction, deep distillation remains directionally near-collinear with TD/MC and fails the same independent validation gate. The evidence supports retaining the accepted low-variance TD finding while moving the diagnosis toward shared gradient/credit-assignment geometry or local evaluator capacity, rather than continuing to vary target semantics.

No search/evaluator infrastructure, TT, root parallelism, semantic transport, or feature-set code changed.
