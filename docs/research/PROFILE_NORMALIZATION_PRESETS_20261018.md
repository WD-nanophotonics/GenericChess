# Static-profile normalization under other setup presets

Auxiliary study by **DEEPSEEK_AUX** (branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18). Independent auxiliary
work, not a PRIMARY mainline result; no other role has rerun it. It follows
`PROFILE_NORMALIZATION_20261018.md` and
`PROFILE_NORMALIZATION_SCALE_20261018.md`, both of which measured only
`setup_preset="classic_like"` and named other presets as an explicit limit.

Private originals: `.local_agent/profile-normalization-presets-20261018/`.
Public copy: `docs/research/data/profile_normalization_presets_20261018/`.
No product code, weight or threshold was changed.

## Question and consumer

Both earlier scans reported zero rounding ties, zero clipping and zero
inversions, but only for `classic_like`. A feasibility probe (seeds
293001-293003) showed `free_random` seed 293002 collapsing two types onto one
normalized integer, so the tie endpoint is reachable in a different setup
regime. The question: at board size 8, do `bilateral_random` and `free_random`
produce rounding ties, clipping or ordering inversions that the `classic_like`
sample never exercised?

The consumer is the same: any statement that normalized board values preserve
raw ratios must be scoped by the setups it was measured on, or extended on
measured evidence.

## Method

Forty fresh rules per preset (seeds 293001-293040), board size 8,
`EvaluationConfig(hand_weight=0.9)`, zero search. The endpoint implementation
is the published `scan_profile_normalization.scan_rule` imported unchanged;
only its `generate_game` binding is wrapped to substitute `setup_preset`
through `dataclasses.replace`. Every endpoint definition (ordering inversions,
ceiling clips, floor value 1, tie groups, material ties at raw ratio >= 1.10,
ratio distortion for raw ratio >= 1.05, the `0.5*(1/v_min+1/v_max)` rounding
bound, hand deviation, promotion consistency) is therefore the same code as in
the published scans.

Plan hash `EC1E8D35...` was recorded with `status: written_before_run` at
`2026-10-18T12:57:43Z`, before any rule was generated. Pre-written decision
rule, applied per preset: any inversion or ceiling clip →
`defect_at_other_presets`; otherwise a material-tie rule fraction of at least
10% → `coarse_normalization_at_other_presets`; otherwise
`ratio_rounding_bounded_persists_at_other_presets`; any pair outside the
rounding bound → `bound_violated`.

## Results

| endpoint | `bilateral_random` | `free_random` |
|---|---|---|
| rules / ordinary types | 40 / 200 | 40 / 200 |
| pairs with raw ratio >= 1.05 | 375 | 379 |
| rules with an ordering inversion | 0 | 0 |
| rules with a ceiling clip | 0 | 0 |
| rules with a floor value of 1 | 0 | 0 |
| minimum / maximum normalized value | 127 / 5552 | 127 / 5552 |
| **rounding tie groups** | **3** | **2** |
| rules with a material tie | 0 | 0 |
| maximum ratio distortion | 0.2507% | 0.3910% |
| median ratio distortion | 0.0338% | 0.0241% |
| pairs outside the rounding bound | 0 of 375 | 0 of 379 |
| largest distortion as a share of its bound | 0.978 | 0.916 |
| promotion checks / inconsistent | 75 / 0 | 70 / 0 |
| hand/board rounding deviation, max | 0.00236 | 0.00236 |
| stored decision | `ratio_rounding_bounded_persists` | same |

Overall decision: `ratio_rounding_bounded_persists_at_other_presets`. The
ordering, clipping and bound endpoints all held; the pre-written material-tie
threshold did not fire, since 5 tie groups in 80 rules is 6.25% and none of
them is material.

The ties are the substantive finding, because they are the endpoint the
`classic_like` sample could not reach:

| preset | seed | shared integer | types | raw scores | raw ratio | material |
|---|---|---|---|---|---|---|
| bilateral_random | 293010 | 1000 | A, P | 4.288465969, 4.288166501 | 1.0000698 | no |
| bilateral_random | 293021 | 1000 | A, X | 6.942469355, 6.943419172 | 1.0001368 | no |
| bilateral_random | 293033 | 1000 | A, C | 2.679364347, 2.678258228 | 1.0004130 | no |
| free_random | 293010 | 1000 | A, P | 4.288465969, 4.288166501 | 1.0000698 | no |
| free_random | 293033 | 1000 | A, C | 2.679364347, 2.678258228 | 1.0004130 | no |

All five groups sit exactly at the median integer, where one rounding step is
0.1% of the value, and every raw ratio is below half a step
(1.00007-1.00041 versus the 1.0005 collapse threshold). All five groups have
**distinct** movement signatures, so this is genuine integer compression of
different capabilities, not the exact-preservation case seen in the earlier
scans. For comparison, the closest *distinct* raw pair under `classic_like` at
size 8 was 1.00557, five times further apart.

## A post-hoc check on what "another preset" means here

This part is **post-hoc and not pre-registered**; it reads two already
measured seeds and one extra preset, and adds no new sample.

- Across the 400 type rows of the two preset blocks there are 199 distinct
  movement signatures, and no signature carries more than one raw capability
  value. The raw capability score is therefore a function of the movement
  signature alone, as the profile code implies.
- Agreement between the two preset blocks is partial: for 23 of 40 seeds the
  capability profiles are identical under both presets (although all 40
  ruleset fingerprints differ, because the preset changes the setup), and for
  17 seeds they differ. The two presets re-draw the same signature for over
  half the seeds rather than giving two fully independent samples.
- Re-running seeds 293010, 293021 and 293033 under `classic_like` at board
  size 8 reproduces the seed 293033 rounding tie (types B/X at 1000, the same
  raw pair) and produces no tie for 293010 or 293021.

Consequently the 5 observed groups should not be read as 5 independent
preset-specific events: one of them (seed 293033) is reproducible under a
third preset and is a property of the capability scale rather than of the
setup; two (seeds 293010 and 293033) come from the subset where both presets
draw the same signature; and one (seed 293021) is unique to the
`bilateral_random` draw. The general statement that survives is the one the
numbers support: at a 1000-median integer scale, capabilities within about
0.05% of each other collapse to one value, and other presets do produce such
pairs at a low but non-zero rate.

## What the results do and do not show

- Rounding ties occur under presets other than `classic_like`, at 5 groups in
  80 rules (6.25% of rules), all at the median integer and all between
  non-material capabilities. The earlier "zero ties" statement is a
  `classic_like` and sample-specific statement, not a property of the profile
  endpoint.
- No inversion, clip, floor-1 value or rounding-bound violation appeared in
  754 ratio pairs, and promotion and hand arithmetic stayed consistent.
- A tie group is a normalization compression fact. It is not evidence that
  the two pieces are strategically equal, and nothing here measures strength,
  playing quality, utility or human prices.
- Scope: two presets, one board size, one seed block, one evaluator weight. The
  post-hoc section shows the preset substitution only partially re-draws the
  capability signatures, which limits how much independence the 80-rule
  sample provides.

## Preserved defect

The first execution wrote its result file and then failed in the console
summary with `KeyError: 'material_tie_groups'` — a summary-printing key name
error, not a computation error. That output is preserved as
`results_profile_presets.first-attempt.json` (`840a2660...`). The fixed run's
`blocks` array is byte-identical to it; only `generated_at_utc`, and therefore
the whole-file hash, differs (`a65013c7...`). No seed, threshold or endpoint
was changed between the two executions.

## Reproduction and integrity

- Plan `EC1E8D35...` recorded with `status: written_before_run` before the scan.
- Deterministic and quick: the replay run took 1.8 s for both presets.
- A replay from a copied script and plan in
  `.local_agent/profile-presets-replay-20261018/` reproduced both blocks, the
  design block, the plan hash, the source hashes and the overall decision
  exactly; `validation_report.json` records those comparisons.
- The scan script byte-compiles, and the stored, first-attempt and replay JSON
  files parse. The scan reports Git HEAD `31878037`.
- The first-attempt/fixed equality, the signature/raw consistency and the
  post-hoc `classic_like` check are recorded in the same validation report and
  in `classic_like_check.json`.

## Publication boundary

Project-relative paths, role/session identifiers, seed numbers and technical
measurements only. A scan of the evidence files for personal paths, account
identifiers, tokens, passwords and API keys returned no hits.
