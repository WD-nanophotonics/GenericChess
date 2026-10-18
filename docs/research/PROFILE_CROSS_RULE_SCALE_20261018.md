# What median normalization removes: per-rule scale

Auxiliary note by **DEEPSEEK_AUX** (branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18). **Secondary, post-hoc
analysis, not pre-registered**: it reads the two already-published profile
scans after seeing their results. It generates no rules, runs no search and
adds no independent sample.

Evidence: `docs/research/data/profile_cross_rule_scale_20261018/`.

## Question

The two scans showed that, *within* a rule, normalized board values preserve
raw ordering and ratios to within 0.51%. A different consumer question was not
answered by them: are values from *different* rules on a common scale?

The source answers this directly. `build_ruleset_profile` divides every raw
capability score by that rule's own non-anchor median before scaling to 1000 and
rounding (`generic_chess/ai/evaluation/profile.py`). Every rule therefore has
median normalized value 1000 by construction, so any per-rule scale factor is
removed. The measurement below asks how large that removed factor actually is
in the sampled rules.

## Measurement

For each of the 120 stored rules (40 at board size 4, 40 at size 6, 40 at
size 8) the per-rule median of ordinary-type raw capability scores was taken
from the published result files.

| board size | rules | raw median min | p25 | p50 | p75 | max | max/min | p75/p25 |
|---|---|---|---|---|---|---|---|---|
| 4 | 40 | 0.742 | 1.348 | 1.804 | 2.655 | 3.671 | 4.95 | 1.97 |
| 6 | 40 | 1.668 | 2.383 | 3.088 | 3.816 | 5.691 | 3.41 | 1.60 |
| 8 | 40 | 2.184 | 3.393 | 3.885 | 4.343 | 8.007 | 3.67 | 1.28 |

Within a single board size the discarded per-rule factor spans 3.4x to 4.9x
between the extreme rules, and the middle half of each block spans 1.28x to
1.97x. Every one of these rules nevertheless reports a median normalized value
of exactly 1000.

## What follows for cross-rule and cross-game ratios

- A normalized value is a **within-rule ratio against that rule's own average
  piece**. Reading the same integer from two rules does not mean the pieces
  have comparable capability; in this sample one rule's median piece can
  correspond to a raw score 3-5x another's.
- Ratio statements that stay inside one rule are supported at the measured
  precision. Ratio statements that cross rules need either the raw scores and
  the per-rule median, or an explicit argument for why the discarded factor is
  irrelevant to the claim.
- This is a structural consequence of the normalization, not a defect: forcing
  a common median is what makes different rules' integers readable at all.
  The cost is that the integers are not a cross-rule currency.

## What this does not show

- Raw capability units are themselves not semantically identical across rules,
  because movement atoms and their configuration weights differ. The 3-5x
  spread is a measure of the discarded normalization factor, not a claim that
  rule A's pieces are "worth" 3-5x rule B's.
- No new rules were generated and no threshold was tested, so this is not
  independent evidence for or against the earlier null results.
- No strength, playing-quality, utility or human-price claim is made.

## Reproduction

```
python docs/research/data/profile_cross_rule_scale_20261018/cross_rule_scale.py
```

The script reads the two published result files, records their SHA-256 values
in its output, and writes `results_cross_rule_scale.json`. It is deterministic
and takes under 0.2 s.
