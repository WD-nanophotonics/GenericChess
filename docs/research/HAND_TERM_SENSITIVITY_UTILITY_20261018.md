# Hand-term root sensitivity and complete-game outcomes on generated 4x4 rules

Auxiliary study by **DEEPSEEK_AUX** (branch `codex/deepseek-aux`, segment
`78213c35-4252-44bb-8c11-acb79a5005e7`, 2026-10-18), continuing the
interrupted segments `d16d7db6-d36f-4a8c-9437-ef210b31df0c` and
`5a983b5e-51ce-4f4a-a249-27784bbe7f97`. This is not a PRIMARY mainline result
and PRIMARY has not adopted it. Evidence: `.local_agent/hand-utility-games-20261018/`
(private); technical inputs, readers, plans, results and hashes are copied to
`docs/research/data/hand_term_sensitivity_utility_20261018/`.
No product code or default changed. The report commit is local to the
auxiliary worktree and unpublished pending GPT outgoing-delta review.

## Question and decision informed

An earlier rule-only ordering probe found that a served hand-term coefficient
(`hand_weight=0.9`) and a hand-blind one (`0.0`) pick different depth-4 root
actions on 7 of 34 rows. Action flips are not utility. This study asks:
at a fixed search budget, does the same coefficient change **complete-game
outcomes** on generated 4x4 rulesets, and can a deeper shared judge separate
configuration preference from move quality?

Decisions informed: whether further hand-policy work has a real utility signal
at this budget, whether an observed game-score difference is a ruleset property
or a depth/termination artefact, and what a defensible future quality test
would have to satisfy. It is not a strength or Elo study.

## Method

`check_hand_term_match.py FIRST_SEED LAST_SEED DEPTH NODE_CAP PAIR_TAG`

- Shipped `AlphaBetaPlayer` root search (`run_root_search`), depth 2 or 3,
  `max_nodes=20000`, quiescence 4 / hard 8, TT off, ordering on, watchdog
  160 plies, fresh searchers per game, in-process replay determinism guard.
- Generated 4x4 `classic_like` rulesets, one start per ruleset: the first
  deterministic-walk state at ply >= 8 with >= 6 legal actions and no
  terminal child. Starts are neutral with respect to the hand term.
- 36 unique seed identities (59..94, one ruleset each), each played at depth 2
  and depth 3 on the **same** start. The unit is 36 seeds x 2 depths = 72
  correlated seed-depth cells, not 72 independent rulesets.
- Two colour-swapped games per seed-depth cell. Arms: `served` 0.9 vs `blind`
  0.0 (comparison, 144 games) and `served` 0.9 vs `served2` 0.9 (control,
  96 games).
- Pair semantics: a *split* means the same colour won both swapped games, i.e.
  the start decided; a *sweep* means the served-configured side won with both
  colours, i.e. the coefficient decided that pair.

## Complete-game outcomes

All 240 games ended in checkmate with 0 problems.

| run | seeds / games | served score | sweeps served / blind | splits | mean plies |
|---|---|---|---|---|---|
| served-blind d2 s59-70 | 12 / 24 | 11.0 = 0.458 | 0 / 1 | 11 | 9.63 |
| served-blind d3 s59-70 | 12 / 24 | 12.0 = 0.500 | 1 / 1 | 10 | 10.00 |
| served-blind d2 s71-94 | 24 / 48 | 31.0 = 0.646 | 8 / 1 | 15 | 14.35 |
| served-blind d3 s71-94 | 24 / 48 | 29.0 = 0.604 | 7 / 2 | 15 | 21.44 |
| served-served d2 s59-70 | 12 / 24 | 12.0 = 0.500 | 0 / 0 | 12 | 11.58 |
| served-served d3 s59-70 | 12 / 24 | 12.0 = 0.500 | 0 / 0 | 12 | 9.58 |
| served-served d2 s71-94 | 24 / 48 | 24.0 = 0.500 | 0 / 0 | 24 | 12.75 |

The same-config controls produce only splits (48/48 over three runs), as
expected for deterministic mirrored play: the start/side decides. They are
determinism/side controls only - they do not remove start-selection,
multiple-look, termination/cost or generality concerns, and say nothing about
rulesets outside these generated seeds.

Search cost moves in both directions with depth/sample. Nodes (qnodes) for
served vs blind: d2 s59-70 6885 vs 7608 (142858 / 131901); d3 s59-70 35547 vs
29908 (467620 / 507006); d2 s71-94 20580 vs 23925 (358987 / 404490). No
consistent cost story.

Short games carry no signal: when both arms finish in <= 7 plies (12/24 at
both depths), 10/12 and 11/12 move sequences are byte-identical, i.e. forced
tactical mates dominated by terminal scores. Divergence concentrates in longer
games (identical sequences only 2/12 and 4/12), whose outcomes were 6-6 and
7-5 in the s59-70 samples.

## What the outcomes do and do not show

- The coefficient is behaviourally active in play on these starts.
- s59-70 (12 seeds, 48 games): served score 0.458 at d2 and 0.500 at d3;
  served sweeps 0/12 and 1/12, blind sweeps 1/12 and 1/12.
- s71-94 (24 seeds, 96 games): served score 0.646 at d2 and 0.604 at d3;
  served sweeps 8/24 and 7/24, blind sweeps 1/24 and 2/24.
- All 36 seeds pooled over both depths: 83 served wins of 144 games (0.576);
  seed-as-unit 12 favoured / 22 neutral / 2 disfavoured, exact sign test
  p = 0.0129. This is **exploratory**: the seed ranges were inspected after
  the first was already null, they are arbitrary consecutive labels rather
  than a characterised rule property, depths reuse one start per seed, and
  several tables were looked at. It is not a confirmed effect size.

The s59-70 / s71-94 labels are seed ranges only, not a ruleset taxonomy, and
this evidence does not establish a formal interaction between the hand term
and any rule feature. A served sweep is a hand-term-caused play change on that
pair, but the sweep-frequency difference between ranges could still reflect
start selection or game length rather than rules. No Elo/WDL estimate, no
all-domain scope, and no product or default change follows.

### Corrections made during review (same data, no rerun)

The first version of this note overstated its statistics. Withdrawn:

1. "72 rulesets" - it is 36 unique seeds x 2 depths, correlated cells.
2. Pooled binomial/sign p values (0.0075 for 15 vs 3; 0.027 for 16 vs 5; 0.039
   for one 8-vs-1 cell) treated seed-depth cells as independent rules. They are
   invalid as independent-rule evidence and are retained only as a historical
   calculation record, replaced by the seed-as-unit test above.
3. "Not a single-cell fluke" and a formal distribution interaction; the ranges
   are labels, not a characterised change.
4. "Served advantage tracks immediate tactical wins": the per-arm
   `root_immediate_win` tally equals the per-arm win tally in all 72 decisive
   d2 games, so it restates the score rather than explaining it.

## Mechanism diagnosis

Three read-only checks on already-saved outcomes; no new seeds or endpoints.

**1. Terminal reasons.** `check_hand_term_match.py` was extended to tally each
arm's search termination reasons per game, and the two d2 cells were replayed
with that instrumentation: 72/72 games reproduced byte-identical move lists,
node counts, qnode counts and summaries. In all 72 decisive d2 games the
losing arm has 0 `root_immediate_win` and the winning arm exactly 1, so per-arm
RIW totals equal per-arm win totals (s71-94 served 31 = 31 wins, blind 17 = 17;
s59-70 served 11 = 11, blind 13 = 13). RIW is collinear with the outcome, not
an explanatory mechanism. Per-arm shares (s71-94: blind completed .9003 /
qsearch-hard .0499 / RIW .0499; served .8649 / .0460 / .0891; s59-70 near
equal .79/.10/.11) differ only in proportion to who won.

**2. Cross-depth seed consistency.** 26/36 seeds have the same win count at
both depths, 10 differ (d3 minus d2: 26 x 0, 5 x +1, 4 x -1, 1 x -2); Kendall
tau on the 0/1/2 seed scores is 0.474 with heavy ties. In s71-94 the
config-decided pairs replicate poorly: d2 sweeps {74,75,76,79,80,84,85,88},
d3 sweeps {72,74,76,78,81,86,88}, overlap only {74,76,88}. s59-70 changes on
1/12 seeds (62). The pooled positive in s71-94 is carried by a minority of
depth-specific sweeps, not by a stable per-seed ruleset property.

**3. First divergence.** Within a colour-swapped pair both games share the
start, so the first index where their move lists differ is the first position
where the arms chose differently. At d2 every sweep first diverges within ply
4 (median 0.5) and at d3 within ply 2 (median 0); 13/36 d2 pairs and 14/36 d3
pairs are byte-identical, i.e. the coefficient changed no move at all. Among
divergent pairs, 13/23 (d2) and 11/22 (d3) still split. The coefficient acts
early and locally, and action divergence is far from sufficient for outcome
divergence - the sensitivity-versus-utility gap measured on these starts. A
ply-0 divergence only means the start is hand-neutral in material, not
action-invariant.

## Judged divergence: does a deeper hand-blind judge prefer the served move?

Plan `judged-divergence/plan.json` (3D193E30) was written before the run. For
each of the 45 cells whose move lists actually diverge (23 at d2, 22 at d3;
the other 27 pairs are byte-identical and, being colour-swapped, always
splits) the shared prefix was replayed, both root candidates regenerated and
asserted equal to the saved move text, and each candidate valued by a third
fixed judge: hand-blind `hand_weight=0.0`, depth 4, 20k nodes, `q 4 hard 8`,
ordering on, TT off, score negated so it is expressed for the mover at the
divergence position; `delta = served - blind`.

Primary result (252 searches, 281 s, no guard trip): `config_decided` 21 cells
served 9 / blind 12; `divergent_split` 24 cells served 4 / blind 16 / tie 4;
totals served 13, blind 28, tie 4. Ten cells re-judge a position the other
depth produced, so there are 35 distinct positions. The pre-written
depth-6/40k tie-break, applied only to the four exact ties within its own
60-search/600-s sub-cap, left 3 ties and moved one cell (seed 93 d3) to
blind-better.

That aggregate does **not** establish that the served moves are worse. The same
positions and candidates judged with the served coefficient 0.9 give 24 served
/ 18 blind / 3 tie with 16/45 sign flips; a third fixed weight 1.8 gives 26 /
18 / 1 with 18 flips (plans B434F2C2; results E4A970A9, 5C030104). The median
absolute difference between judges' deltas is 1009 at weight 0.9 and 2025 at
1.8, against a median |delta| of 1003 for the primary judge: the verdict moves
with the judge's own coefficient at roughly the magnitude of the effect being
measured. On these positions a deeper search with a single scalar evaluator
measures **configuration preference**, not configuration-free move quality.

The one weight-stable subset is tactical: in 7 cells (5 distinct positions) one
candidate's child returns |value| >= 1e9 (a terminal node inside the searched
tree), with the same sign at all three weights: 5 favour blind, 2 favour
served. The term is therefore neither uniformly harmful nor uniformly helpful
even in this strongest subset. Truncation can also drop such a score: for seed
60 d2 both candidates score +999999998 at weights 0.0 and 0.9, whereas at 1.8
the blind child's quiescence search cut off after 6 nodes and returned a static
-3849, turning a tie into an apparent +1e9 delta. Mate claims under
alpha-beta/hard-limit truncation are judge-reported scores, not proofs.

## Truncation strata: do the verdicts survive completed evaluation?

Plan `plan-truncation-strata.json` (8C9E07D9), zero new searches. Of the 45
judged cells, 14 completed depth 4 for both candidates, 17 had exactly one
candidate truncated and 14 had both, so 31/45 (69%) contain at least one
`node_limit` or `qsearch_check_hard_limit` evaluation.

| stratum | cells | served | blind | tie |
|---|---|---|---|---|
| both evaluations completed | 14 | 7 | 5 | 2 |
| one truncated | 17 | 3 | 14 | 0 |
| both truncated | 14 | 3 | 9 | 2 |

Excluding the four tie-break cells gives 7/5 completed, 14/3 one-truncated and
9/3 both-truncated. Counting each seed once per stratum, the completed stratum
is 4 seeds served / 3 blind / 3 mixed over 10 seeds, while the truncated
strata are 14 blind / 4 served / 2 mixed over 20 seeds. The pre-written rule
("no blind majority in the completed stratum") fires:
`decision = no_blind_majority_in_completed_stratum`.

The same stratification on the 35 distinct positions (`plan-distinct-position-strata.json`
7C5A0516, AB26ED42, 396982CC) gives 13 completed (7 served / 4 blind / 2 tie),
13 one-truncated (3/10/0) and 9 both-truncated (2/6/1); no position's two
occurrences disagree about the stratum. Nine cells reach |delta| >= 1e9 at one
or more weights and eight involve a truncated evaluation; the only mate-scale
cell with both evaluations complete (seed 90 d2) favours served at all three
weights.

There is no symmetric criterion in this data. Over the three weights the
majority verdict is 24 served / 20 blind / 1 mixed, but that majority is
effectively the {0.9, 1.8} pair (agreement 40 and 42 of 45 cells versus 29 for
the 0.0 judge), so it is a stability diagnostic, not a configuration-free
test.

## Completion check on the same judge

Plan `plan-complete-truncated-judged.json` (B43AC36E; script 56E2F1DE) was
written before the run. The 31 truncated cells were rebuilt and re-valued by
the same hand-blind depth-4 judge on a fixed node-cap ladder
`20000 -> 40000 -> 80000 -> 160000`, stopping at the first `completed_depth`.
At 20k every candidate had to reproduce the saved score, reason, nodes and
qnodes.

Result 618EEED9 (291 searches, 602.3 s, 2,045,965 nodes+qnodes; caps 400/900
not hit; no interruption or problem):

- 62/62 candidate evaluations reproduced exactly at 20k; 0
  `instrument_unstable`, 0 `rebuild_failed`.
- 10 of 31 cells completed both candidates: 7 blind / 2 served / 1 tie, with
  8/10 recorded-sign agreement. The two flips are seed 64 d3 (`+10` -> served,
  recorded blind) and seed 76 d3 (`0` -> tie, recorded blind); both are
  single-digit or zero margins, i.e. ties/quantization rather than preference
  reversals.
- Seed majority inside the newly completed part: 4 blind / 1 served / 2 mixed
  over 7 seeds, so the pre-written `newly_completed >= 10` branch fires with
  `blind_direction_survives_completion`. This is threshold-exact and weak.
- Merged completed set: 24 cells = 9 served / 12 blind / 3 tie; 22 distinct
  positions = 9 served / 10 blind / 3 tie; seed majority over 14 seeds = 5
  blind / 3 served / 6 mixed.
- 21 cells stayed truncated, and after the 160k rung **all 33
  non-primary-completed arms** end at `qsearch_check_hard_limit` (9
  primary-completed arms at `completed_depth`; no `node_limit` survives). The
  residual truncation is the fixed 8-ply quiescence hard check - structural
  for this instrument, not node scarcity.

## Second instrument (diagnostic only)

The frozen 618EEED9 also intended a separate secondary instrument (depth 4,
80k nodes, `q 4 hard 16`, weight 0.0, TT off, ordering on), but created its
`Budget` together with the primary one, so the secondary 600 s clock contained
the whole 602.3 s primary phase and tripped after 14 searches
(`problems` = `max_seconds 600.0 hit before secondary seed79 d2 served`;
`guards.secondary_elapsed_seconds` = 602.3, identical to the primary).
C1-C3 are unaffected; C4 kept only 8 of 21 cells' secondary records (11
`completed_depth` + 3 `node_limit` arm reasons; 1 tie and 2 blind verdicts,
no scores). The frozen file was not edited.

A bounded completion phase (`plan-secondary-completion.json` A4616098, script
3431B063, written before running, clock starting at the phase boundary)
finished only the 19 missing evaluations, reusing the 14 frozen arm reasons
read-only. Result AE5F8A46: 96 phase searches, 224.0 s, 784,763 nodes+qnodes,
no interruption or problem.

- Secondary arm reasons over the 33 non-primary arms: 25 `completed_depth` /
  8 `node_limit`.
- Pair status over the 21 cells: 9 `mixed_instrument` (one arm completed under
  the primary ladder, so no comparable verdict), 3 `reused_verdict` (seed 60
  d2 tie, seed 69 d2 and 70 d2 blind), 6 `incomplete` (seeds 67, 71, 74 at
  both depths), 3 `computed`.
- Six secondary verdicts: 2 tie / 3 blind_better / 1 served_better, agreeing
  with the recorded verdict in 4/6. The disagreements are seed 69 d2 and d3
  (recorded served_better, primary delta `+11` both; secondary blind_better).
  The d3 secondary scores are served 1244 vs blind 1248, a 4-point margin; for
  d2 the frozen file kept only the verdict. A 4- and an 11-point margin on two
  sides of zero is overlap/quantization, not a demonstrated reversal. Seed 88
  d2 keeps its sign at mate scale (secondary served -392 vs blind
  -999999993), and seed 60 d3 reproduces its tie (both 999999998).

Per the pre-written rule the decision is `diagnostic_only`: no primary
endpoint, direction or decision changes, and the secondary verdicts are never
pooled with the primary ones.

## Move-class concentration of the first divergence

Two zero-search readers (`judged-divergence/move-class/`, plans written before
running) classify the two first-divergence moves of each judged cell as drop,
promotion or quiet board move, and compare the choices with the legal-action
mix at the same 35 distinct positions.

Of the 45 cells, 30 change action class between arms and 29 contain a drop on
at least one side; 16 contain a promotion and only 7 are quiet-vs-quiet. Every
one of the 29 drop cells has the drop on the blind side: 15 served-quiet /
blind-drop, 7 served-promotion / blind-drop, 7 drop-vs-drop. The served arm
chooses 7 drop / 13 promotion / 25 quiet; the blind arm 29 / 4 / 12.

That shift is large against availability: at the 35 distinct positions there
are 420 legal actions, 192 drops (45.7%), 48 promotions (11.4%) and 180 quiet
moves (42.9%). Blind drops are over-represented by +18.7 points; served drops
are under-represented by -30.2 points and served promotions over-represented
by +17.5. The coefficient therefore does not only change which quiet move is
picked; it changes the action-class mix at the divergence point. This makes
the adopted caution concrete: a scalar comparison that ignores drop/promotion
structure would misdescribe what this coefficient does, even though the tally
says nothing about which class is better.

Two limits are worth stating. Availability is a uniform legal-move baseline,
not the arms' policy distribution, so over-representation is not error. And
the blind arm shares `hand_weight=0.0` with the judge; but the blind-leaning
verdicts are not concentrated in the blind-drop cells (17 blind / 9 served / 3
tie there versus 11 / 4 / 1 elsewhere), so a shared-coefficient class
preference does not by itself explain the aggregate verdict. The
`plan-move-class.json` threshold (class-changing pairs >= 15 of 45) fired at
30, so on this fixture the promotion/drop caution applies to the divergence
loci as well as to the rule semantics.

## Conclusion and limits

The hand-policy **quality** question stays UNKNOWN for this instrument.
The coefficient is behaviourally active, action divergence is not outcome
divergence, and a deeper search carrying the same scalar hand term measures
configuration preference. The completion check shows the same judge's
blind-leaning direction is not created solely by the 20k cap, but the residual
truncation is structural and a second instrument moves 2/6 verdicts on
4-11-point margins. A defensible future quality attempt needs (i) budgets that
complete the intended depth or explicit truncation-aware scoring of cut-off
lines, (ii) a criterion that does not share the coefficient under test
(matched-seed game outcomes, or a judge with no hand term scoring forced
continuations), and (iii) seed-level units with endpoints written in advance.

Limits: deterministic single-start games, depth 2-3 arms at 20k nodes, 36
generated seeds, several cells inspected, correlated seed-depth cells, no
p-values, no independent rerun by another role, and no exploration of deeper
play budgets where the original ordering flips were measured. Nothing here is
a strength, generality or auxiliary-state claim; the move-class section is a
descriptive tally of chosen actions at divergence points, not a policy
distribution or per-class utility claim, and the searched rules used the full
shipped transition semantics without this study testing them.

## Preserved defects and corrections

1. First version used `GameSession` from the initial position; every game was
   1 ply (immediate mate). Replaced with mid-game `apply_action` play.
2. `native_test_helpers` import was pytest-dependent; replaced with inline
   `generated_compiled`.
3. `NameError: seed`, `KeyError: 'blind'` in the control, and a shadowed `first`
   variable (unhashable dict) - fixed before the recorded runs.
4. Recorded `design.search.use_tt` said `true` while the call always passed
   `use_tt=False`, so the four earliest files' metadata is wrong on that one
   field (actual search behaviour is TT-off). Originals are frozen as
   produced.
5. The 48-game s71-94 d2 run overwrote the original 24-game s59-70 d2 file
   (output names lacked the seed range; raw original lost). The cell was
   reproduced deterministically (same summary: 11-13, 0.4583, 9.625 plies,
   nodes 6885/7608, qnodes 142858/131901, 84.7 s) and now carries `_s59-70`.
   That file is a reconstruction, not the lost original.
6. The secondary clock-scope defect and the AE5F8A46 note-string wording
   ("11 reasons" while the structured list contains 14) are recorded above;
   the structured values are authoritative and the frozen result was not
   rewritten.

## Reproduction

See `docs/research/data/hand_term_sensitivity_utility_20261018/README.md` for
the copied readers, plans, results, full hashes and the exact rerun commands.
Readers that use `Path(__file__).parent` must be run from a reconstructed
`.local_agent/hand-utility-games-20261018/` scratch layout with the project
root on `PYTHONPATH`; the game-result files are frozen inputs for every later
reader. No published command reruns a frozen outcome.
