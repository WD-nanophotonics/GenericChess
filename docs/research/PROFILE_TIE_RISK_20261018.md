# Rounding-tie risk grows with types per rule

Auxiliary note by **DEEPSEEK_AUX** (branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18). The size-by-preset scan
below was **pre-registered before it ran**; the gap/headroom section that
follows it is explicitly **post-hoc** and derived from the same stored result.
No search is involved anywhere.

Evidence: `docs/research/data/profile_tie_risk_20261018/`.

## Question

The published profile scans measured tie presence at one board size per
preset: none at board sizes 4, 6 or 8 under `classic_like`, and five tie groups
at size 8 under `bilateral_random` and `free_random`. Neither design varied
*types per rule* and preset together, so the practical risk that a richer rule
compresses two genuinely different piece capabilities into one normalized
integer had never been measured.

The mechanism matters for the rule-only price target. Normalization rounds
`1000 * raw / median(raw)` to an integer, so the rounding error available to
two neighboring capabilities is of order `0.5/v` grid units, where `v` is the
smaller normalized value. More ordinary types per rule means more within-rule
pairs to collide and, through the median, a different scale — but the direction
of the net effect is not obvious a priori, which is why it was pre-registered
as a falsifiable prediction rather than assumed.

## Pre-registered design

| item | value |
|---|---|
| presets | `classic_like`, `bilateral_random`, `free_random` |
| board sizes | 4, 6, 8 (3, 4, 5 ordinary types) |
| seeds per preset | 120 fresh (294001-294120, 295001-295120, 296001-296120) |
| cells | 9 |
| rules | 1,080 |
| ratio pairs (raw ratio >= 1.05) | 6,499 |
| search | none |
| endpoint | tie groups per cell, plus material ties, inversions, clips, floor-1, distortion, quantization bound, promotion consistency |
| pre-written rule | non-decreasing counts in all three presets **and** strictly higher at 8 than 4 in at least two |
| measured runtime | 14.19 s |

A tie group is two or more ordinary types sharing one normalized integer while
their raw scores differ. Ties were required to be non-decreasing from size 4 to
6 to 8 within each preset because the within-rule pair count grows 3 -> 6 -> 10.

## Result: the pre-written decision fired

`tie_risk_increases_with_types_per_rule`. All three preset profiles are
non-decreasing, and all three are strictly higher at size 8 than at size 4.

| preset | size 4 | size 6 | size 8 |
|---|---:|---:|---:|
| `classic_like` | 1 | 6 | 7 |
| `bilateral_random` | 2 | 3 | 3 |
| `free_random` | 1 | 3 | 4 |

Pooled over the three presets (360 rules per size):

| board size | rules with a tie | share | Wilson 95% (descriptive only) |
|---|---:|---:|---|
| 4 | 4 | 1.11% | 0.43-2.82% |
| 6 | 12 | 3.33% | 1.92-5.74% |
| 8 | 14 | 3.89% | 2.33-6.42% |

30 tie groups (32 member pairs) in total, none material (no within-group raw
ratio reached 1.10), no inversions, no ceiling clips, no floor-1 values, no
promotion inconsistencies, and no quantization-bound violations. The 31 pairs
that compare distinct raw scores span ratios `1.0000078` to `1.0006947`, so
every one is a sub-0.07% compression. The 32nd pair sits inside one
three-member group and has bitwise-identical raw scores under a different
movement signature: that is equal measured capability, not compression, and it
is excluded from the tied-pair counts below. No pair inside any tie group
shares a movement signature.

An exploratory Fisher exact comparison of the pooled size-4 and size-8 rule
counts gives `p = 0.0289`; 4 vs 6 gives `0.0736` and 6 vs 8 gives `0.8421`.
None of the three per-preset 4-vs-8 comparisons is significant
(`0.066`, `1.000`, `0.370`). This test was **not** pre-registered.

## Post-hoc: what actually decides a collision

The tie counts alone cannot say how close a non-tying pair came, so a second,
clearly post-hoc analysis recomputed the exact normalized scores from the
stored raw values and asked which pairs lie within one rounding grid unit.

Checks first. Reconstructing `exact = 1000 * raw / median(raw)` and
`max(1, min(round(exact), MAX_STATIC_EVAL))` reproduces **all 5,040 stored
board integers exactly** (0 mismatches), so the reconstruction is the real
normalization, not an approximation. And, as the definition requires, **no tie
occurred outside `exact_gap < 1`** in any of the nine cells — the necessary
condition holds with zero exceptions.

| board size | pairs with gap < 1 | of which equal score | distinct score | tied | adjacent escapes | conversion (distinct score) | rules with a distinct-score gap < 1 | rules that tied |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 8 | 3 | 5 | 4 | 1 | 80.0% | 5 | 4 |
| 6 | 18 | 5 | 13 | 12 | 1 | 92.3% | 13 | 12 |
| 8 | 27 | 9 | 18 | 15 | 3 | 83.3% | 17 | 14 |

A sub-unit gap is necessary but not sufficient: two values inside one unit can
still land in adjacent integers, and at size 8 three of 18 distinct-score near
pairs do. So a "near-equal pair" is a candidate, not a tie. Pairs whose two raw
scores are exactly equal are shown separately: they have a zero gap by
construction but cannot be a compression tie (the tie definition requires
distinct raw scores), so including them in a conversion denominator would
understate the conversion. All 17 such pairs across the scan have different
movement signatures; only one of them lies inside a tie group (the 32nd pair
discussed above).

The per-rule headroom is the more portable quantity. Taking each rule's
nearest pair with distinct raw scores gives a median of 250, 127 and 74 grid
units at sizes 4, 6 and 8 (pooled over presets): a typical rule is nearly two
orders of magnitude away from collision. Only 17 of 360 size-8 rules have a
distinct-score pair within one unit; 8 further rules have only an equal-score
pair at zero gap.

That median hides a long tail, which is the part a consumer with a tolerance
choice actually cares about. Counting rules whose nearest distinct-score pair
is closer than `k` grid units (pooled over presets, 360 rules per size):

| `k` | size 4 | size 6 | size 8 |
|---:|---:|---:|---:|
| 1 | 5 (1.4%) | 13 (3.6%) | 17 (4.7%) |
| 5 | 6 (1.7%) | 21 (5.8%) | 29 (8.1%) |
| 20 | 22 (6.1%) | 42 (11.7%) | 70 (19.4%) |
| 100 | 79 (21.9%) | 145 (40.3%) | 223 (61.9%) |

So the collision risk is concentrated: most rules are far from a boundary,
but at size 8 nearly one rule in five is within 20 grid units and three in
five are within 100. A single median understates that tail.

Two further observations bound how this should be read:

- 50 of the 53 near pairs had their smaller exact value at or just above the
  normalization anchor: median 1000.0 at size 4, 1130-1191 at size 6 and
  1000-1004 at size 8, with only three pairs below 999. Pairs involving the
  median type are the ones that can collide, which is a direct consequence of
  median normalization, not a property of the movement atoms.
- The raw-ratio screen `<= 1.001` selected exactly the same pairs as
  `gap < 1` in all nine cells, with the largest reachable raw ratio at
  `1.00079`. This is not a second criterion: a tie requires
  `(raw_ratio - 1) * smaller_exact_value < 1`, and the observed maximum of
  that product was 0.894 (0.79 and 0.69 at sizes 4 and 6), while the smallest
  gap at or above one unit was 1.41. Because the near pairs sit at a smaller
  exact value near 1000, `1 + 1/v` is close to `1.001`, so the ratio screen
  nearly coincides with the grid condition in this sample. The coincidence
  would break at a different anchor scale: at exact value 5000, a ratio of
  1.0006 is already more than one grid unit apart.

## What follows for the rule-only price target

- Integer profiles are not a lossless price summary for complex generated
  rules, and the compression rate is a function of rule complexity, not one
  number. A single "tie rate" quoted for the generator would understate rich
  rules.
- Ties are small when they happen: at most 0.07% of a ratio, never material by
  the 1.10 threshold, and never between identical movement encodings.
- For any consumer that needs exact within-rule ordering, the headroom measure
  (nearest distinct gap in grid units) is the quantity to report, because it
  says how far a rule is from the next collision instead of only whether one
  already occurred.

## Limits

- The 120 seeds are a single fresh block per preset and are **shared across
  the three board sizes**, so cells are paired, not independent. Capability
  signatures also repeat across seeds, so the Wilson intervals and the Fisher
  test describe the sample; they are not a population inference.
- Counts per cell are 1-7. The three-preset agreement is the reason to take
  the ordering seriously; no single preset would support it alone.
- One generator family, one evaluator configuration (`hand_weight=0.9`), three
  presets. Promotion and hand terms were checked for consistency but were not
  varied.
- Tie presence is a normalization fact, not a statement that the two pieces
  are strategically equal, and no strength, playing-quality, utility or
  human-price claim is made. No game was played and no search was run.

## Reproduction

```
python docs/research/data/profile_tie_risk_20261018/scan_tie_risk.py
python docs/research/data/profile_tie_risk_20261018/analyze_gap_headroom.py --summary-only \
  --out /tmp/results_gap_headroom.json
```

The scan writes `results_tie_risk.json` (plan hash, source hashes and Git HEAD
embedded); the gap analysis reads that file, finds the checkout root by walking
up to `generic_chess/`, and reproduces
`results_gap_headroom.summary.json` byte-for-byte. The public summary omits the
per-pair array; running without `--summary-only` regenerates it. Both are
deterministic and need no search.
