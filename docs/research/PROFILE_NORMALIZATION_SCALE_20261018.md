# Static-profile normalization at board sizes 6 and 8

Auxiliary study by **DEEPSEEK_AUX** (branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18). Independent auxiliary
work, not a PRIMARY mainline result; no other role has rerun it. It continues
the question in `PROFILE_NORMALIZATION_20261018.md`, which measured the served
profile at `board_size=4` where a rule carries only three ordinary types, and
explicitly left larger type sets untested.

Private originals: `.local_agent/profile-normalization-scale-20261018/`.
Public copy: `docs/research/data/profile_normalization_scale_20261018/`.
No product code, weight or threshold was changed.

## Question and consumer

The generator's default geometry is `board_size=8`, not the 4x4 case measured
first. With more ordinary types per rule there are more pairs for integer
rounding to collapse, and each rule's weakest piece can sit further from the
median. The question: does the bounded-rounding result survive at
`board_size=6` (four ordinary types, six pairs) and `board_size=8` (five
ordinary types, ten pairs)?

The consumer is the same as before: whether normalized board values can stand
in for cross-rule ratio evidence, or whether the earlier statement must stay
scoped to the toy geometry.

## Method

Forty fresh rules per size (seeds 292001-292040), `classic_like`,
`EvaluationConfig(hand_weight=0.9)`, zero search. The endpoint implementation
is imported directly from the published 4x4 scan
(`scan_profile_normalization.scan_rule`, SHA-256 `2a8f630d...`) with its board
size overridden, so inversions, clips, tie groups, ratio distortion, hand
deviation and promotion checks are defined by exactly the same code as before.

Plan `1838EC98...` was written and hashed before the run. It pre-registered one
additional falsifiable prediction: independent integer rounding allows a pair's
ratio error to reach `0.5 * (1/v_min + 1/v_max)` where `v_min` and `v_max` are
the two normalized integers, so any distortion above that bound is a defect in
the reasoning rather than a new threshold.

Pre-written decision rule: any inversion or ceiling clip →
`defect_at_larger_size`; otherwise a material-tie rule fraction of at least
10% at either size → `coarse_normalization_at_larger_size`; otherwise
`ratio_rounding_bounded_persists`; any pair outside the rounding bound →
`bound_violated`.

## Results

| endpoint | size 6 | size 8 |
|---|---|---|
| rules / ordinary types | 40 / 160 | 40 / 200 |
| types per rule | 4 | 5 |
| pairs per rule / pairs with raw ratio >= 1.05 | 6 / 233 | 10 / 384 |
| rules with an ordering inversion | 0 | 0 |
| rules with a ceiling clip | 0 | 0 |
| rules with a floor value of 1 | 0 | 0 |
| minimum / maximum normalized value | 178 / 3138 | 158 / 3706 |
| rules with any tie group | 0 | 0 |
| rules with a material tie | 0 | 0 |
| maximum ratio distortion | 0.2549% | 0.2634% |
| median ratio distortion | 0.0377% | 0.0295% |
| pairs outside the rounding bound | 0 of 233 | 0 of 384 |
| largest distortion as a share of its bound | 0.979 | 0.988 |
| promotion checks / inconsistent | 66 / 0 | 74 / 0 |
| hand/board rounding deviation, max | 0.00204 | 0.00196 |
| stored decision | `ratio_rounding_bounded_persists` | same |

Across 617 ratio pairs at the two larger sizes, no inversion, clipping, tie
compression or bound violation appeared. The maximum distortion was lower than
the 0.5049% seen at 4x4, and that difference is explained by granularity, not
by board size: the smallest normalized value was 101-103 in the 4x4 block but
158-178 here, and error on a ratio scales with `0.5/v_min`. The bound check
confirms the mechanism — observed distortions reached 98-99% of the
`0.5*(1/v_min+1/v_max)` ceiling but never crossed it.

How close did rounding come to collapsing a pair? The smallest within-rule raw
ratio between *distinct* capability scores was 1.00722 at size 6 and 1.00557 at
size 8; those pairs rounded to integers 8 apart and 6 apart, and the smallest
gap among the closest six pairs was 5. A tie was therefore not reachable at
this resolution in this sample. The three pairs with
*exactly* equal raw scores (one at size 6, two at size 8) all had identical
movement signatures and mapped to identical integers, which is exact
preservation rather than compression.

## What the results do and do not show

- At the generator's default geometry, and at the intermediate size, the
  served profile preserved raw ordering and ratios within 0.27%, with no ties
  or clipping in 80 rules and 617 measured pairs.
- The mechanism is now measured rather than inferred: ratio error is governed
  by the smaller normalized value, and the `0.5*(1/v_min+1/v_max)` bound held
  for every pair. A rule with a very weak piece (normalized value near 1) would
  therefore carry up to ~50% error on ratios involving it. That regime was not
  sampled: the weakest value observed anywhere was 101.
- Zero ties is a statement about this generator's capability spread plus the
  1000-median integer scale, not a guarantee. A rule whose two types differed
  by less than about one part in a thousand in raw capability would tie.
- Promotion gains and hand values remained internally consistent; that is
  arithmetic consistency, not evidence of strategic correctness.
- No strength, playing-quality, utility or human-price claim is made, and the
  result does not extend to non-square or rectangular boards, other setup
  presets or other movement families.

## Reproduction and integrity

- Plan hash `1838EC9890069CBD3EDDE5E78A6F15F89D6D13327C112126C63DD3FD418508CB`
  recorded in `plan-log.json` with `status: written_before_run` before the scan.
- The scan is deterministic and took 1.3 s. It writes one JSON result holding
  both size blocks, the plan hash, the imported endpoint script hash, source
  hashes and Git HEAD `8e6c56f3`.
- A replay from a copied script and plan in `.local_agent/profile-scale-replay-20261018/`
  reproduced both blocks exactly; the result and plan JSON parse, and the scan
  script byte-compiles.
- No seeds, sizes, thresholds or endpoints were retuned after seeing either
  result. The 4x4 block was not rerun.

## Publication boundary

Project-relative paths, role/session identifiers, seed numbers and technical
measurements only. A scan of the evidence files for personal paths, account
identifiers, tokens, passwords and API keys returned no hits.
