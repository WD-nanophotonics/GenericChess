# H50 F53 learning-signal variance and target comparison

Status: completed on 2026-09-04. Parent checkpoint: `8f89bbd523aa054ff5b83b27d31b089e930686a3`.

## Scope and protocol

This diagnostic kept semantic search, evaluator behavior, and the five existing feature blocks frozen. It used four independent deterministic batches of eight trajectories per ruleset, with 400-node trajectories and four distillation points per trajectory. The batch seeds were `5300000`, `5301000`, `5302000`, `5303000` for Western Chess and `5400000`, `5401000`, `5402000`, `5403000` for Standard Shogi. Deep current-v2 self-distillation used 4,000 nodes.

Validation used two disjoint, fixed slices of the existing S49-M bundle: `[32:48]` and `[48:64]`. Teacher surfaces were generated at 20k, 40k, and 80k nodes; no S49-M[16:32] selection data from F51/F52 was reused for the validation decision.

The three targets were computed from the same trajectory points: current TDLeaf(lambda=0.7), Monte Carlo terminal return, and deeper current-v2 search self-distillation. Target directions were compared by cosine and unit-vector distance, then all candidate probes used one common frozen normalization with a diagnostic fraction of `0.0005` (0.05% of the full parent L2 norm). This common scale prevents a fixed-step saturation artifact from being mistaken for target quality.

## Direction variance

Full-vector norms and Native-effective parameter counts by batch:

| Ruleset | Batch | Full norm | Board | Hand | Dynamic | Native-effective |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Western | 0 | 0.30790 | 0.01080 | 0 | 0.30771 | 8 |
| Western | 1 | 0.22631 | 0.00635 | 0 | 0.22622 | 8 |
| Western | 2 | 0.19856 | 0.00994 | 0 | 0.19831 | 7 |
| Western | 3 | 0.28960 | 0.01048 | 0 | 0.28941 | 8 |
| Shogi | 0 | 3.30486 | 0.01395 | 0.03522 | 3.30464 | 14 |
| Shogi | 1 | 3.94725 | 0.01421 | 0.02571 | 3.94714 | 16 |
| Shogi | 2 | 2.52573 | 0.01104 | 0.01724 | 2.52564 | 17 |
| Shogi | 3 | 3.92619 | 0.01523 | 0.04448 | 3.92591 | 16 |

All six full-vector pairwise cosines were 0.999410–0.999862 for Western and 0.999936–0.999980 for Shogi. The lowest block cosines were Western board 0.85208 and Shogi board 0.61134; dynamic was at least 0.99961/0.99995 respectively. Sign consistency was Western full 0.96875 (board 0.95, hand 0, dynamic 1) and Shogi full 0.91304 (board 0.86538, hand 0.96429, dynamic 1). The zero Western hand value means that block had no active signal in these samples, not contradictory signs.

Cumulative full norms at 8/16/24/32 trajectories were Western `0.30790/0.53415/0.73264/1.02224` and Shogi `3.30486/7.25204/9.77769/13.70383`. Cosine to the previous cumulative direction at 16/24/32 was Western `0.999915/0.999967/0.999999` and Shogi `0.999989/0.999997/0.999998`. The sampled TD signal is therefore low-variance in direction; the question is target alignment, not batch noise.

## Target direction comparison

Target direction cosine matrices were nearly collinear:

| Ruleset | TDLeaf vs MC | TDLeaf vs distill | MC vs distill | Largest unit distance |
| --- | ---: | ---: | ---: | ---: |
| Western | 0.996500 | 0.996480 | 0.999998 | 0.08390 |
| Shogi | 0.985017 | 0.985115 | 1.000000 | 0.17311 |

Distillation labels had 32 points per batch. Western label means were `-0.2433`, `-0.3809`, `-0.2216`, `-0.2813`; Shogi means were `-0.2813`, `-0.4375`, `-0.4375`, `-0.2813`. Label ranges were Western approximately `[-1.0000, 1.0000]` and Shogi `[-1.0000, 1.0000]`.

At the common 0.05% diagnostic magnitude, target agreement did not improve over the parent on either fixed validation slice:

| Ruleset | Target | Native-effective | `[32:48]` target / parent | `[48:64]` target / parent | Flip rate | Mean abs displacement |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Western | TDLeaf(lambda) | 8 | 0.4375 / 0.4375 | 0.3125 / 0.3125 | 0.25 / 0.125 | 4,072.9 / 7,181.3 |
| Western | Monte Carlo | 8 | 0.4375 / 0.4375 | 0.3125 / 0.3125 | 0.25 / 0.125 | 4,086.1 / 7,171.5 |
| Western | Deep distill | 8 | 0.4375 / 0.4375 | 0.3125 / 0.3125 | 0.25 / 0.125 | 4,085.6 / 7,168.4 |
| Shogi | TDLeaf(lambda) | 16 | 0.2500 / 0.4375 | 0.1250 / 0.6250 | 0.6875 / 0.8125 | 10,696.1 / 7,746.7 |
| Shogi | Monte Carlo | 20 | 0.2500 / 0.4375 | 0.1250 / 0.6250 | 0.6875 / 0.6875 | 10,520.8 / 7,597.9 |
| Shogi | Deep distill | 20 | 0.2500 / 0.4375 | 0.1250 / 0.6250 | 0.6875 / 0.6875 | 10,522.3 / 7,598.8 |

Teacher stability from 40k to 80k was Western 0.9375 on `[32:48]` and 0.8750 on `[48:64]`; Shogi was 1.0 on both slices. Thus the negative target result is not explained by an unstable teacher surface.

## Saturation self-check and conclusion

An initial 5% full-vector probe produced 93.75–100% move flips and roughly 270k–360k mean score displacement. That run was treated as a diagnostic failure mode, not as evidence of target misalignment. The corrected 0.05% common-normalization run above separates magnitude from direction and still gives the same negative selection outcome.

The formal F53 classification is **`TD_TARGET_OR_CREDIT_ASSIGNMENT_MISALIGNED`** for both rulesets: batch and cumulative directions are stable, but none of TDLeaf(lambda), terminal-return Monte Carlo, or deeper search distillation generalizes to either held-out validation slice. No learnable child or arena was created. Search/evaluator infrastructure and all five feature blocks remain unchanged.

Transient Heavy JSON, console output, generated binaries, and Courier state remain outside Git; this ADR-style report and the durable regression tests are the retained evidence.
