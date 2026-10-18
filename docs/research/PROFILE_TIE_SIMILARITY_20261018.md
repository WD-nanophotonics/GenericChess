# Rounding ties concentrate among overlapping movement signatures

Auxiliary note by **DEEPSEEK_AUX** (branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18). The decision rule was
**pre-registered before the analysis ran**; the matched-reference contrast and
the exactness decomposition are explicitly **post-hoc** and descriptive. No
search, new rule or new seed is involved anywhere.

Evidence: `docs/research/data/profile_tie_similarity_20261018/`.

## Question

The closed tie-risk study found 31 distinct-score tied pairs in 1,080 generated
rules: normalized board integers that collide although the raw scores differ by
a ratio of `1.0000078` to `1.0006947`. Every collision is therefore a
sub-0.07% compression. What the scan did not measure is whether the two
capabilities behind a tie are near-aliases in movement, or capabilities with
little movement in common.

That distinction changes how a consumer should read a tie. If ties join
capabilities whose movement token sets already overlap, the integer collision
is the last step of a near-duplication and carries little syntactic
information loss. If ties join dissimilar capabilities, the same integer hides
a real movement difference. Neither case is a strength or utility claim.

## Pre-registered design

| item | value |
|---|---|
| inputs | published tie-risk result plus its private per-pair gap detail |
| new rules / seeds / search | 0 / 0 / none |
| tied set | 31 distinct-score tied pairs (raw ratio > 1, exact gap < 1, equal stored integer) |
| reference set | all 6,811 distinct-capability pairs in the same nine cells |
| signature | one token per stored movement entry; set Jaccard over tokens |
| endpoint | tied and reference distributions plus one decision |
| pre-written rule | tied median >= reference p90: `benign_concentration`; <= p75: `dissimilar_ties`; otherwise `inconclusive_similarity` |
| measured runtime | under 1 s, reading the stored 3.3 MB result |

## Result: the pre-written decision fired

`benign_concentration`, on the pooled tied median.

| group | n | median set Jaccard | reference percentile |
|---|---:|---:|---:|
| tied pairs | 31 | 1.00000 | 100.0% |
| reference pairs | 6,811 | 0.72727 | p90 = 1.00000 |

By board size the tied medians are all 1.0:

| board size | tied n | reference n | tied median | tied Q1-Q3 |
|---|---:|---:|---:|---|
| 4 | 4 | 1,074 | 1.0 | 0.775-1.0 |
| 6 | 12 | 2,152 | 1.0 | 1.0-1.0 |
| 8 | 15 | 3,585 | 1.0 | 1.0-1.0 |

Tied set-Jaccard histogram: 25 pairs at 1.0, two at 0.90, one at 0.889, two at
0.778, one at 0.70.

## The percentile threshold is degenerate

The pre-written rule compares against the reference 90th percentile, and that
percentile is exactly 1.0: 778 of 6,811 reference pairs (11.42%) already share a
token set. The rule therefore fires, but the p90 comparison is not a sharp
separation. The informative contrast is the reference **median** 0.727, and
the matched-reference check below.

## Post-hoc exactness: overlap is not duplication

| comparison | pairs | share |
|---|---:|---:|
| identical stored signature string | 0/31 | 0.0% |
| identical movement multiset | 15/31 | 48.4% |
| identical movement token set | 25/31 | 80.6% |

Set Jaccard 1.0 means no movement token is unique to either capability. It
does not mean the capabilities are the same: no tied pair has an identical
signature string, and 16 of 31 differ in token multiplicity. Six pairs sit
below 1.0, between 0.70 and 0.90, where some movement is genuinely unique to
one side. The 31 pairs span 22 unordered signature-string pair classes.

## Post-hoc matched-reference contrast

The tied pairs have token-set size pairs 8v8 (16), 9v9 (11), 8v9 (2) and 9v10
(2). Restricting the non-tied reference to the same size pairs removes the
token-count composition difference and leaves 4,961 pairs.

| comparison | tied | matched non-tied reference |
|---|---:|---:|
| same token set | 25/31 = 80.6% | 601/4,961 = 12.1% |
| median set Jaccard | 1.000 | 0.778 |
| median multiset Jaccard | 0.977 | 0.538 |

A two-sided Fisher comparison of the same-token-set counts gives
`p = 6.57e-18`. The pairs share types and rules, so this is a descriptive
contrast, not an independent-sample test.

The multiset metric points the same way, so the result is not an artifact of
ignoring multiplicity. The tied median sits at percentile 99.2% of the matched
reference on multiset Jaccard.

## What the near-collision population looks like

The closed gap analysis separates the near pairs into three groups. Post-hoc
similarity medians on the same 31 tied pairs:

| group | n | set Jaccard median | multiset Jaccard median |
|---|---:|---:|---:|
| tied, distinct score | 31 | 1.000 | 0.977 |
| equal-score, escaped to adjacent integers | 17 | 1.000 | 1.000 |
| distinct-score, escaped to adjacent integers | 5 | 0.727 | 0.586 |

The equal-score escaped pairs are as similar as the tied pairs, so
`benign_concentration` describes the near-collision population rather than
isolating a tie-specific causal bias. The comparison that is specific to
distinct-score compression points the other way, but it has only five pairs
and supports no inference on its own.

## Interpretation and limits

- Ties in this sample overwhelmingly join capabilities whose movement token
  sets overlap; 25 of 31 share a token set and 15 share the full multiset.
- Overlap is not identity: no pair has the same stored signature string, and
  six pairs retain movements unique to one side.
- A collision of two overlapping capabilities is a low-syntactic-information
  compression, not a proof that the two are strategically interchangeable.
  Board geometry, capture interaction, promotion and drop context are not
  represented by token overlap.
- No strength, playing-quality, utility, human-price or game-outcome claim is
  made. The sample is 31 pairs in 22 signature classes, one generator family
  and `hand_weight 0.9`; the five escaped distinct-score pairs are too few for
  inference.
- The reference includes 17 exactly equal-scored pairs, 295 distinct pairs
  below the tie scan's 1.05 ratio screen and 6,499 screened pairs; the
  matched-reference check uses only non-tied pairs.

## Reproduction

`analyze_signature_similarity.py` reproduces the pre-registered block from the
stored tie-risk result. `posthoc_matched_reference.py` then adds the exactness
reconciliation and matched-reference block; re-running both scripts
reproduces `results_signature_similarity.json` and `tied_pairs.json`
byte-identically. File hashes, the plan hash and the exact-rational Fisher
check are recorded in the evidence README.
