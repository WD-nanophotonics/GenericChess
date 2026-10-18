# Excluded quiet drops in quiescence: blind threats and served-root value

Auxiliary study by **DEEPSEEK_AUX** (branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18). This is an independent
auxiliary question, not a PRIMARY mainline result; PRIMARY has not adopted it
and no role has independently rerun these searches. Evidence originals are in
the Git-ignored `.local_agent/qsearch-drop-exclusion-20261018/`; the plans,
scripts, results and hashes are copied to
`docs/research/data/qsearch_drop_exclusion_20261018/`. No product code,
default, search cap or frozen panel was changed.

## Question and consumer

The served quiescence policy (`classify_noisy`) includes checking and terminal
drops but excludes ordinary quiet drops from the noisy set. The question:
on generated 4x4 drop rules, does that leaf exclusion hide a materially
meaningful drop, and do positions containing a blind-threat drop show a larger
served depth-2 versus depth-3 score change? The consumer is whether even-depth
comparisons (such as the earlier hand-term d2 panel) need a drop-aware
quiescence caveat, or whether this policy is empirically harmless in the owned
generated panel. This is a search-horizon measurement, not a strength study.

The exclusion is a **leaf quiescence** policy, not a root action filter: the
depth-2/depth-3 root search still enumerates every legal drop. Accordingly the
study also records when the served search actually chose an excluded drop.

## Method

All positions come from `generate_game` (`board_size=4`, `setup_preset`
`classic_like`) and a deterministic start walk. Each start requires at least
6 legal actions and no terminal child. The evaluator is the served
`hand_weight=0.9` profile. Searches use `run_root_search` with
`max_nodes=20000`, quiescence depth 4 / hard depth 8, TT off, ordering on,
depths 2 and 3, plus a descriptive depth-4 record.

An **excluded drop** is a legal drop for which `classify_noisy` returns false,
with a non-terminal child that does not give check. A **blind threat** is a
new attack by the mover on an enemy-occupied square that no enemy piece
attacks after the drop (pseudo-attack geometry; pins are ignored). A
**profitable blind threat** requires the target's board value to exceed the
dropped base type's value.

Four bounded stages:

1. **Stage 1** (plan `0C9FC09A`): seeds 101-112, one position each, up to 4
   offsets, pre-written rule requiring at least 3 positions with a blind
   threat plus a 2x median-delta or flip-rate criterion.
2. **Stage 2** (plan `D626580B`): a fresh confirmatory panel, seeds 113-160,
   offsets 0-11, with a materially refined profitable-threat endpoint and a
   non-mate horizon endpoint. Parents whose stored d2 or d3 score is at or
   beyond `MATE_THRESHOLD` are excluded from the horizon comparison.
3. **Bounding** of every profitable case: legal reply enumeration, a depth-1
   child confirmation against the parent static score, and a depth-3 /
   200,000-node re-search.
4. **Addendum** (exploratory, plan `C674043B`): every excluded drop's child
   searched to depth 2 (three plies from the parent) and compared with the
   parent's served d3 score, which is the depth-matched test; the parent d2
   comparison is reported only as a shallower reference.

## Results

### Stage 1: two blind threats, no support

Seeds 108 and 111 produced no eligible start within 4 offsets and are retained
as missing, not replaced. The 10 eligible positions gave 70 legal drops:
57 excluded quiet drops and 13 checking drops. Thirteen excluded drops created
some new enemy attack, but only 2 created a blind threat (seeds 105 and 112),
and neither target was worth more than the dropped base type (value gaps -321
and -1332). Both depth-1 confirmations were below the parent static score.

The pre-written rule returned `supported=false`, outcome `no_support`: the
blind group had 2 positions, below the required 3. Its median absolute
d2-to-d3 score change (804.5) exceeded twice the rest median (1.5), so the
delta criterion alone fired, but the group-size condition did not. This is a
sample-size failure, not evidence for the alternative.

Three excluded drops were nevertheless served at d2/d3 (seed 102 `X@d3` at d2,
seed 102 `X@a4` at d3, seed 112 `X@c1` at d2). Excluded-at-the-leaf drops are
still legal and sometimes selected by the full-width root search.

### Stage 2: four profitable blind threats in 238 excluded drops

All 48 seeds 113-160 produced a position; no seed is missing and no problem
was recorded. The panel contains 323 legal drops: 238 excluded quiet drops and
85 checking drops, with 0 terminal drops and 0 classification cross-check
mismatches. Sixty excluded drops (25.2%) created some new enemy attack,
23 (9.7%) created a blind threat, and **4 (1.68%) were geometrically
profitable**. The one-sided 95% Wilson upper bound on the per-excluded-drop
rate is 3.69%.

Eight blind-threat drops landed on a square attacked by the enemy and not
defended by the mover. One blind threat (seed 127 `A@c4`) had a depth-1
confirmation above the parent static score, but it was not a profitable
threat.

Horizon endpoint, restricted to the 29 non-mate positions:

| group | positions | median abs(d3-d2) | action flips |
|---|---|---|---|
| >=1 blind-threat drop | 8 | 212.5 | 2 (0.250) |
| no blind-threat drop | 21 | 11 | 5 (0.238) |

The pre-written delta criterion fired and the flip criterion did not, so the
stored outcome is `support`; it is an **association only**. The group values
are bimodal (`[0, 0, 0, 0, 425, 598, 1824, 2110]`), so the median is not a
typical position. Post hoc, excluding the four profitable positions leaves
6 group positions with median 511.5. Ten positions in total hit the
`qsearch_check_hard_limit` somewhere: seven non-mate (2/8 in the group, 5/21
in the rest) and three mate-bound. A further three mate-bound positions ended
at `node_limit`. Seven of 48 positions changed action between d2 and d3.

Five records in four positions served an excluded drop at d2/d3: seed 134
`P@d3` at d3 (a blind threat), seed 155 `A@a1` at d2 and `P@a1` at d3,
seed 156 `A@a1` at both depths, and seed 159 `P@d3` at d3. **None of the four
profitable cases is among them.**

### The four profitable threats at depth 1 and a larger cap

| seed | drop | target | target / drop value | replies | capture dropped | target escape | terminal reply | depth-1 mover | parent static |
|---|---|---|---|---|---|---|---|---|---|
| 124 | `P@c2` | X | 1000 / 708 | 16 | 0 | 0 | 0 | -1914 | 1220 |
| 147 | `P@b3` | A | 1084 / 1000 | 14 | 0 | 2 | 3 | -999999999 | 3780 |
| 147 | `X@d3` | A | 1084 / 905 | 14 | 0 | 2 | 3 | -999999999 | 3780 |
| 150 | `P@d3` | A | 2109 / 1000 | 14 | 2 | 0 | 0 | -4 | 1800 |

All four depth-1 mover values are below the parent static score; in two cases
the opponent has an immediate win. A depth-3 search with a 200,000-node cap
chose a different root action in every case (scores 802, 999999997,
999999997 and 5691 respectively); the drop remained unchosen. Descriptive
"best static value after reply" figures were above the parent in all four
rows, but they fall after a legal opponent reply and are not quality evidence:
for seed 124, for example, the best static reply leaves 1297 while the
depth-1 search returns -1914. Geometry ignores pins, and one legal reply list
is not a proof of best play.

### Addendum: no excluded drop valued above the served d3 root

All 48 positions and 238 excluded drops completed; the phase took 39.56 s and
was not interrupted. The parents split into 29 non-mate (120 excluded drops)
and 19 mate-bound (118 excluded drops).

| comparison (non-mate parents) | strictly above parent | exact ties |
|---|---|---|
| child depth 2 (3 plies from parent) vs parent d3 | 0 | 4 |
| child depth-2 vs parent d2 (shallower reference) | 3 | - |

The four depth-matched ties are seeds 134 `P@d3` (-3821), 155 `P@a1` (5259),
156 `A@a1` (2479) and 159 `P@d3` (-1240). A zero-search cross-check shows
**all four were themselves served by the depth-3 search** (156 also at d2),
so the equality is a self-consistency check, not an unserved drop matching the
root value. The three shallower-reference positives (seed 155 `P@a1` +45,
seed 156 `A@a1` +109, seed 159 `P@d3` +21) are all exact ties under the
depth-matched comparison.

The static check is intentionally a sanity control, not a finding: 120/120
non-mate excluded drops have a "better" static mover value than the parent
because a drop adds material to the board. That sign is trivial. One
mate-bound drop (seed 117 `A@d1`) was +1 against the parent d3 score; it is
excluded from the improvement comparison and no 200,000-node confirmation
exists for it because no non-mate candidate exceeded the parent.

## What the results do and do not show

- In the 48-position panel, 4 of 238 excluded quiet drops made a geometrically
  profitable blind threat (1.68%, upper 3.69%). Each was refuted by the
  depth-1 reply search and none was chosen at 200,000 nodes.
- No excluded drop in this panel was valued strictly above the served
  depth-matched root choice. The four ties were served actions themselves.
- The non-mate d2/d3 horizon association met the pre-written delta criterion
  (group median 212.5 vs 11) but not the flip criterion; it is descriptive,
  threshold-dependent, bimodal and partly truncated, and does not establish
  that blind-threat drops cause the larger score change.
- A served search can choose a drop that the leaf quiescence policy excludes.
  The exclusion therefore concerns leaf evaluation, not legal availability.
- These are score-sensitivity measurements. A higher or lower search score is
  not playing strength, utility or a policy recommendation. Ties, mate scores,
  truncation and overlapping optimal sets can explain single-action
  differences.
- Pseudo-attack geometry ignores pins, so "undefended" is approximate. One
  position per generated rule and one fixed seed range are not a population
  statement about the generator or about other rule families.

## Reproduction and integrity checks

- Stage-1 analysis was rerun after fixing its repository-root resolution; the
  regenerated `analysis_stage1.json` is byte-identical to the pre-fix file
  (SHA-256 `CDD95009...`), so its counts are reproducible.
- Stage-2 analysis was recomputed from the stored panel with 0 mismatches.
- Replay from the source scripts matched all 15 compared fields for seeds
  124, 127, 147 and 150, and again for seeds 117, 134, 155, 156 and 159.
  Replay uses the same stored offsets and regenerates the rules and starts.
- Plans and their hashes were recorded before their runs in
  `plan-log.json`, `plan-log2.json` and `plan-log-addendum.json`; the source
  hashes in those logs pin the engine files used.
- The zero-search tie/chosen cross-check reads only the two stored result
  files and is reproduced in the public copy.

## Preserved defects and corrections

1. `plan_stage2.json` records `created_at_utc: 2026-10-18T12:50:00Z`, but its
   filesystem mtime is 12:29:52Z and `plan-log2.json` / the results are
   12:35:08Z. The timestamp field is a clerical error; the plan and its
   recorded hash `D626580B...` are the file that preceded the run, and no
   decision rule changed.
2. The first stage-2 execution completed the searches but failed while
   serializing a `Square` to JSON, so **no output file was written**. The
   driver was fixed and rerun; only the successful rerun is evidence.
3. `analyze_stage1.py` initially resolved the repository root incorrectly.
   It was corrected to use the project root and rerun; the output is identical
   to the original, which is retained privately as
   `analysis_stage1_original.json`.
4. The public copies of `results_addendum.json`, `stage2-analysis.json` and
   `bound_profitable_cases.json` rewrite exactly one field, `source_result`,
   from an absolute private path to the project-relative path. All other
   public files are byte-identical to their private originals.

## Publication boundary

No personal information, credentials, keys or account identifiers are
included. The report and data contain project-relative paths, role and session
identifiers, seed numbers and technical results only. Private originals remain
in the Git-ignored `.local_agent/qsearch-drop-exclusion-20261018/`.
