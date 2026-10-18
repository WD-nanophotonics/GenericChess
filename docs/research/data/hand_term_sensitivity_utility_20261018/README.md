# Public evidence copy: hand-term sensitivity versus complete-game utility

Auxiliary study by **DEEPSEEK_AUX**, branch `codex/deepseek-aux`, segment
`78213c35-4252-44bb-8c11-acb79a5005e7` (2026-10-18), continuing the interrupted
segments `d16d7db6-d36f-4a8c-9437-ef210b31df0c` and
`5a983b5e-51ce-4f4a-a249-27784bbe7f97`. Report:
`docs/research/HAND_TERM_SENSITIVITY_UTILITY_20261018.md`.

This is not a PRIMARY mainline result and PRIMARY has not adopted it. Earlier
execution labels in the source artifacts (the legacy `DeepSeekPRIMARY` name)
record where the run happened before the role split; they do not make this a
mainline study or an instruction to replace PRIMARY. Owner of this copy is
DEEPSEEK_AUX; the private originals stay in the Git-ignored
`.local_agent/hand-utility-games-20261018/`.

The study asks whether a served hand-term coefficient (`hand_weight=0.9`) versus
a hand-blind one (`0.0`) changes complete-game outcomes on generated 4x4
`classic_like` rulesets at a fixed node budget, and whether a deeper shared judge
can separate configuration preference from move quality. It is a sensitivity and
instrument study, not a strength/Elo study.

## What is here

Top level (13 files):

- Frozen game results (7): `results_hand_term_match_served-blind_d{2,3}_n20000_s{59-70,71-94}.json`
  (the comparison arms) and `results_hand_term_match_served-served_d{2,3}_n20000_s59-70.json`
  plus `..._served-served_d2_n20000_s71-94.json` (the same-configuration
  determinism/side controls). These are the frozen inputs for every later
  reader; no command here regenerates them.
- Reason tallies (2): `results_hand_term_match_served-blind-reasons_d2_n20000_s{59-70,71-94}.json`,
  produced by the instrumented replay of the two depth-2 comparison runs.
- Readers (4): `check_hand_term_match.py` (the search driver that produced the
  game files), `summarize_reasons.py`, `analyze_seed_consistency.py`,
  `analyze_pair_divergence.py` (read-only over saved results).

`judged-divergence/` (20 files):

- Plans written before their runs (6): `plan.json`,
  `plan-judge-robustness.json`, `plan-truncation-strata.json`,
  `plan-distinct-position-strata.json`, `plan-complete-truncated-judged.json`,
  `plan-secondary-completion.json`.
- Results (7): `results_judged_divergence.json`,
  `results_judged_divergence_servedjudge.json`,
  `results_judged_divergence_w18judge.json`,
  `results_judged_divergence_strata.json`,
  `results_judged_divergence_distinct_strata.json`,
  `results_complete_truncated_judged.json`,
  `results_secondary_completion_judged.json`.
- Scripts (6): `check_judged_divergence.py` (the judge driver),
  `summarize_judged_divergence.py`, `stratify_judged_divergence.py`,
  `distinct_position_strata.py`, `complete_truncated_judged.py`,
  `complete_secondary_phase.py`.
- One determinism smoke record: `smoke-d2-s59.json`, byte-identical to the seed
  59 depth-2 record in the primary result.

`judged-divergence/move-class/` (6 files, added 2026-10-18 after the first copy):

- Plans written before their analyses (2): `plan-move-class.json`,
  `plan-legal-move-baseline.json`.
- Results (2): `results_move_class_tally.json` (class of both first-divergence
  moves per judged cell, crossed with verdict, pair kind and completion) and
  `results_move_class_baseline.json` (legal-action class mix at the 35 distinct
  positions, with served/blind choice shares against it).
- Readers (2): `tally_move_class.py` and `baseline_legal_move_mix.py`. Both read
  only frozen inputs and refuse to overwrite their results; neither runs a
  search. The baseline reader regenerates each position with the stored
  `sample_start` rule and applies the saved prefix moves, asserting the action
  `repr` round-trip and that both games share the prefix.

The 39 technical files above total 1,172,522 bytes, and each is byte-identical
to its private original (verified by SHA-256 on 2026-10-18, 0 mismatches).
This README is additional: it has no private counterpart and is not part of that
count or hash table.

## Frozen hashes (SHA-256, upper case)

| file | sha256 |
|---|---|
| analyze_pair_divergence.py | `ADABECB894D041767A3D20450A6066CA59D6B27D25500BDCBCA3F30F6BE3B5D3` |
| analyze_seed_consistency.py | `0154643F3CF0BB46FD9BF60DB9C428D07AA627DCF1066466C5991E546C44D779` |
| check_hand_term_match.py | `412938DF47616C6581AB9FA7049DE322B9B66E2229FBA3F1EDE9ACDA0127AAC5` |
| judged-divergence/check_judged_divergence.py | `791115DC0D1E73F0E2F78224587015FF1671B8DB1A47B2B3F95A84AB3CBD953D` |
| judged-divergence/complete_secondary_phase.py | `3431B0638C9CFCE4DC7F55A0867C202A27B0B1F4BD24787D19E70BB3EE28780A` |
| judged-divergence/complete_truncated_judged.py | `56E2F1DEAA9AD2B6864D61CF4DBD850805393B6D0D057A18EF31F6853F9D79EA` |
| judged-divergence/distinct_position_strata.py | `AB26ED42ED8941DBB7C71670DE02E49B612DEB3FE47F3C1A9915130FF7637C60` |
| judged-divergence/move-class/baseline_legal_move_mix.py | `111063C3A4DB193BB6F5914BA119737D12D6B302F8DBB61720004F4685FFEA91` |
| judged-divergence/move-class/plan-legal-move-baseline.json | `8C5604B07CB1B4AFF497A999432FBF5BD352AA67AEE896CF6C7DCBE3B20386A1` |
| judged-divergence/move-class/plan-move-class.json | `78729045E2D044B3FE21AC081CD3FF8A6424830667EDAE3447A277A63CC2A55A` |
| judged-divergence/move-class/results_move_class_baseline.json | `DCA269F1BC58C1F82D8EA278FB48FCCD9A49ECBEB2C3272C0118B18060C7FBAF` |
| judged-divergence/move-class/results_move_class_tally.json | `6BAAECEA139F41CD477D8D44FB78760F2FA8D72D2ED50AE4C504FDF9B4AFF75C` |
| judged-divergence/move-class/tally_move_class.py | `3A522A1FD3DD48B9A5F2A591C9A64D1FA3774F487B5F8E65A22D09C25D1BA161` |
| judged-divergence/plan-complete-truncated-judged.json | `B43AC36E7EF3E48D6ACEE055E3A2C10CB4C3A87EB226F40392C88A2A976A8C79` |
| judged-divergence/plan-distinct-position-strata.json | `7C5A0516995120B649963D31D722B4C418B13443D9D1E1642DC7B159CAF7C769` |
| judged-divergence/plan-judge-robustness.json | `B434F2C21EB21BB59C252EBFA550D2A431E1526BC872D0FDB257B1F331CC18DA` |
| judged-divergence/plan-secondary-completion.json | `A46160984D2CEE03459F7368F05C2967AE0759B2A15633F5D6CCA326E39263C0` |
| judged-divergence/plan-truncation-strata.json | `8C9E07D981CA9CE88D4A0563659F20FA721595A69EBACD0CB5DA327ED68CCDA8` |
| judged-divergence/plan.json | `3D193E307BBF949372F98A59CEB72CD09C45F9467B31A0799B5631A4F1A28AD0` |
| judged-divergence/results_complete_truncated_judged.json | `618EEED9E5EB324EDC380D95F03ACC2ED1BF1A9FB7463F9D0CCEAC4B1529EC21` |
| judged-divergence/results_judged_divergence_distinct_strata.json | `396982CC640183C935F15BEE05977723962D1A00FA89663CE50D53F240E34741` |
| judged-divergence/results_judged_divergence_servedjudge.json | `E4A970A93985B22F5F5CF134FC9845943A28D17E070B12E3D79E911520BCE921` |
| judged-divergence/results_judged_divergence_strata.json | `F8808A6BAA31D07692C3C6A5AB9BBF8FA5BB2A1FE620A47583D497AE0396B68C` |
| judged-divergence/results_judged_divergence_w18judge.json | `5C0301049086CD8A4139C90B356A5DEBF9DF9EDE533DC2B8BFC071B7004E197E` |
| judged-divergence/results_judged_divergence.json | `444CDA2632E59ABBB06A2C747AA22A0488385C38C7E987E1B3B70B3434882979` |
| judged-divergence/results_secondary_completion_judged.json | `AE5F8A463F3A301ED3E38D73FE7AA5FCB35C9EF04C8905EB2632BB0B20861045` |
| judged-divergence/smoke-d2-s59.json | `279A3D51E4E35E9E888C51603A2FA7D056C811B4D35E191BD1CB86CE2B150FC6` |
| judged-divergence/stratify_judged_divergence.py | `2F1A5DF725EDEC54F2465D3A130D0E6352B357504E348306446319F374EDB037` |
| judged-divergence/summarize_judged_divergence.py | `949B2A550F35D8931270E990EB184246804641136CC927182C37D581821A0B60` |
| results_hand_term_match_served-blind_d2_n20000_s59-70.json | `B83FE7EB9989A5852E924CB7AB000F941A01CFE831CD9D38E11ABFB5A30E1F01` |
| results_hand_term_match_served-blind_d2_n20000_s71-94.json | `CA7BE8851B9193C7F6B073EEC1ACAB4D6EBA73B540B88D668F56C25FC17EC77C` |
| results_hand_term_match_served-blind_d3_n20000_s59-70.json | `0F5B4BDDB9F886A2FE3B46A7249BA50B1A0A578097C011D188D4151E5A2AB25B` |
| results_hand_term_match_served-blind_d3_n20000_s71-94.json | `6F153E666727E9F494FB9ED36F9A05B9DDD3A7198B4DAB8C054AAC0E1DB56359` |
| results_hand_term_match_served-blind-reasons_d2_n20000_s59-70.json | `4DCAA63C0489DD92F240D1CD258458D43A2B91B1ECFF12BD70BADD71A0D853E7` |
| results_hand_term_match_served-blind-reasons_d2_n20000_s71-94.json | `5F8C8DB29AFFAB2FAE74FA2C6836F4449EC4D9D5A2DB1F80671ACB9F6911E29F` |
| results_hand_term_match_served-served_d2_n20000_s59-70.json | `3B6CC674198371B996030C4BCF63DE233570AEA640FA5B97ADDA8A62650132B3` |
| results_hand_term_match_served-served_d2_n20000_s71-94.json | `1B28BA7520051B5709E403D14635D06BCA474FD040174A5D6064367CB4C9B36E` |
| results_hand_term_match_served-served_d3_n20000_s59-70.json | `6779F542595890FA615A4BA2E4B1E09C8AFBAF8C08887D1107B95DAD1684B09C` |
| summarize_reasons.py | `8C68C3A410A3D5DAEFEEB7B438028D437AA622B16129754816659BD532B7D2EB` |

The plans record the inputs they were written against (inline hashes in the
plan bodies), so a reviewer can see that each endpoint predates its run.

## Reproduction

All readers below were re-run by DEEPSEEK_AUX on 2026-10-18 in a fresh scratch
tree built from this directory; results are quoted from that run.

**1. Reconstruct the scratch layout.** The scripts resolve their data with
`Path(__file__).parent`, so the copy must sit under the expected private path
name. Never reconstruct over the private originals.

```powershell
# run from the project root, where the project's .venv lives
$py = '.venv/Scripts/python.exe'
$root = (Resolve-Path '.').Path
$scratch = Join-Path $env:TEMP 'gc-hand-utility-public-20261018'
$data = Join-Path $scratch '.local_agent/hand-utility-games-20261018'
New-Item -ItemType Directory -Force -Path $data | Out-Null
Copy-Item 'docs/research/data/hand_term_sensitivity_utility_20261018/*' $data -Recurse -Force
$env:PYTHONPATH = $root
Push-Location $scratch
```

**2. Saved-data readers (no search).**

```powershell
& $py '.local_agent/hand-utility-games-20261018/summarize_reasons.py'
& $py '.local_agent/hand-utility-games-20261018/analyze_seed_consistency.py'
& $py '.local_agent/hand-utility-games-20261018/analyze_pair_divergence.py'
& $py '.local_agent/hand-utility-games-20261018/judged-divergence/summarize_judged_divergence.py'
```

Verified outputs from that run:

- `summarize_reasons.py`: the two depth-2 reason tables, e.g. s71-94 blind
  shares `.9003 / .0499 / .0499` and served `.8649 / .0460 / .0891`, and the
  summary lines `served_win 31 / served_loss 17`.
- `analyze_seed_consistency.py`: `seeds with both depths: 36`,
  `d3 minus d2 {-2: 1, -1: 4, 0: 26, 1: 5}`, `Kendall tau 0.4743`, s71-94
  d2 sweeps `[74, 75, 76, 79, 80, 84, 85, 88]`, d3 sweeps
  `[72, 74, 76, 78, 81, 86, 88]`, overlap `[74, 76, 88]`.
- `analyze_pair_divergence.py`: depth 2 identifies 13 identical-line pairs,
  23 divergent (13 splits, 8 served sweeps, 2 blind sweeps); depth 3 identifies
  14 identical-line, 22 divergent (11 splits, 8 served sweeps, 3 blind sweeps).
  Served sweeps first diverge at max ply 4 (median 0.5) at depth 2 and max
  ply 2 (median 0) at depth 3.
- `summarize_judged_divergence.py`: prints `stored aggregate verdict counts
  match recomputation`, 45 judged / 27 no-divergence cells, 252 searches,
  35 distinct positions with 10 duplicated across depths, the primary
  `config_decided` 9 served / 12 blind and `divergent_split` 4 / 16 / 4 tie,
  the tie-break `3 tie / 1 blind_better`, and the weight-0.9 and weight-1.8
  judge totals (24/18/3 with 16 sign flips, median judge-delta gap 1009;
  26/18/1 with 18 flips, median gap 2025; median primary |delta| 1003).

**2b. Move-class readers (no search).** In a scratch tree, delete the copied
`results_move_class_*.json` first so the overwrite guard does not stop the
reader (never do this in the private originals):

```powershell
Remove-Item '.local_agent/hand-utility-games-20261018/judged-divergence/move-class/results_move_class_tally.json'
Remove-Item '.local_agent/hand-utility-games-20261018/judged-divergence/move-class/results_move_class_baseline.json'
& $py '.local_agent/hand-utility-games-20261018/judged-divergence/move-class/tally_move_class.py'
& $py '.local_agent/hand-utility-games-20261018/judged-divergence/move-class/baseline_legal_move_mix.py'
```

Verified outputs from that run: `tally_move_class.py` reports 45 judged cells,
30 class-changing pairs, 29 cells involving a drop, 16 involving a promotion,
7 quiet-vs-quiet, and decision
`class_changing_share_at_or_above_one_third`; `baseline_legal_move_mix.py`
reports 45 cells / 35 distinct positions / 0 prefix mismatches, 420 legal
actions (drop 192, promotion 48, quiet 180; shares .4571 / .1143 / .4286),
served choices 7 drop / 13 promotion / 25 quiet, blind choices 29 / 4 / 12,
blind drops over-represented by 18.7 points and served drops
under-represented by 30.2 points against that availability, and 5 of the 7
quiet-vs-quiet cells had a legal drop.

**3. Overwrite guards (expected to refuse).** Both strata writers assert the
stored aggregate and then refuse to replace their result file:

```powershell
& $py '.local_agent/hand-utility-games-20261018/judged-divergence/stratify_judged_divergence.py'
& $py '.local_agent/hand-utility-games-20261018/judged-divergence/distinct_position_strata.py'
```

Verified: each prints `refusing to overwrite existing result ...` and exits 1.
That is the intended positive check, not a failure.

**4. What is not rerun here.** `complete_truncated_judged.py` and
`complete_secondary_phase.py` execute live search (291 and 96 searches
respectively) and would rewrite frozen results, so they are included for
review only. `check_hand_term_match.py` and `check_judged_divergence.py` are the
original drivers; they too regenerate outcomes rather than check them. Every
frozen outcome, plan hash and reader assertion is reproducible from the saved
files above without any of those four commands.

## Scope and honest limits

- 36 generated `classic_like` 4x4 seed identities, one deterministic start
  each, played at depth 2 and 3 with `max_nodes=20000`, quiescence 4 / hard 8,
  TT off. The 72 seed-depth cells are correlated, not 72 independent rulesets.
- All 240 recorded games ended in checkmate with 0 problems. The same-config
  control runs are determinism/side controls only.
- The pooled served score (83/144) and the seed-level sign test (12 favoured /
  22 neutral / 2 disfavoured, exact two-sided p = 0.0129) are exploratory: the
  seed ranges were inspected after the first was already null and several
  tables were looked at. They are not a confirmed effect size, strength, Elo or
  generality claim.
- The judged-divergence aggregate measures the judge's configuration, not
  configuration-free move quality: the verdict moves with the judge's own
  hand weight at roughly the magnitude of the effect measured.
- The move-class tally classifies only the **chosen** first-divergence actions
  and compares them with the legal-action mix at the same positions. Drops are
  45.7% of legal actions there; the blind arm's 29/45 drop choices are
  over-represented by 18.7 points and the served arm's 7/45 by -30.2, so the
  coefficient changes the action-class mix. This is not evidence that drops or
  promotions are better or worse, and the judge shares the blind arm's
  coefficient. Blind-drop cells are not where the blind-leaning verdicts
  concentrate (17 blind / 9 served / 3 tie of 29, versus 11 / 4 / 1 of 16
  elsewhere), so a shared-coefficient class preference does not by itself
  explain the aggregate verdict.
- Within the completion check, the blind-leaning direction survives at the
  pre-written 10-cell threshold, but that branch is threshold-exact and weak;
  the residual truncation is the fixed 8-ply quiescence hard check, structural
  for this instrument. The secondary instrument moved 2 of 6 verdicts on
  4-11-point margins, so its role is `diagnostic_only`.
- The `_s59-70` depth-2 game file is a deterministic reconstruction: the
  original was overwritten by a later run whose output names lacked the seed
  range (report defect 5). The reconstructed summary matches the recorded one
  (11-13, 0.4583, 9.625 plies, nodes 6885/7608, qnodes 142858/131901) but it is
  not the lost original.
- The secondary clock in `results_complete_truncated_judged.json` contains the
  primary phase (`guards.secondary_elapsed_seconds` 602.3 equals the primary,
  and `problems` records the 600 s trip). The frozen file was not edited; the
  bounded phase in `results_secondary_completion_judged.json` starts its clock
  at the phase boundary. In that file the note string says "11 reasons" while
  the structured list contains 14; the structured values are authoritative.
- The earliest four game files record `design.search.use_tt = true` while the
  driver always passed `use_tt=False`; actual search behaviour is TT-off and
  the frozen originals were left as produced.

## Publication boundary

No personal information, credentials, keys or account identifiers are included.
Only project-relative paths, role identifiers, ruleset/seed numbers and
technical results appear. The private README, `claim.json` and the interruption
report remain in the Git-ignored `.local_agent/` originals and are not part of
this copy; none of them is needed to read or check the results here.
