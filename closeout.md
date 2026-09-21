## Gate 2 controlled anchor-pressure closeout

This in-place `CAUSAL_DIAGNOSTIC` replaced raw "any checking move" with a
controlled one-ply anchor-pressure witness. Eligible states require all
children nonterminal, both checking and nonchecking actions, strict best-check
advantage over the best noncheck, and an all-checking global production-
evaluator argmax. Expected actions are exactly that argmax; primary/reviewer
use fixed depth 1 and weak128 remains telemetry.

Chess and Shogi each found and passed controlled witnesses. Chess's best-check
advantage was 1516 and both primary/reviewer completed in 19 nodes; Shogi's
advantage was 731 and both completed in 95 nodes. The first generated ruleset,
`generated_L_V4-3`, had no controlled anchor witness in the fixed corpus, so it
records `NOT_OBSERVED / NO_CONTROLLED_ANCHOR_WITNESS_IN_BOUNDED_SCAN` and its
capability suite continued to PASS.

The run then reached `generated_F_V4-3` and stopped at `mobility` with
`failure_type=HARD_FAILURE`; controlled material had passed first. No later
ruleset, short game, Gate 3, or evolution ran. Gate 2 remains failed and Gate 3
frozen.

Focused verification passed:

```text
pytest -q tests/test_gate2_merged_benchmark.py
4 passed
```

## Gate 2 controlled drop-witness closeout

This in-place `CAUSAL_DIAGNOSTIC` replaced the raw any-drop expected set with
a controlled one-ply witness. Eligible states require all children
nonterminal, at least one drop and non-drop, strict best-drop advantage over
the best non-drop, and an all-drop global production-evaluator argmax.
Expected actions are exactly that argmax; primary/reviewer use fixed depth 1,
while weak128 remains telemetry.

The accepted Shogi witness has 79 legal actions (71 drops, 8 non-drops), best
drop score 267 versus best non-drop 191, and one unique best pawn drop. Primary
and reviewer both completed depth 1 in 159 nodes and selected it; controlled
drop passed. Static capability witnesses are normalized to identical fixed
search roots so bounded-scan descendants have consistent imported history;
positions, expected sets, evaluator scores, and budgets are unchanged.

The merged run continued into `generated_L_V4-3`. Controlled material and the
existing mobility task passed, then `anchor_danger` stopped as
`HARNESS_FAILURE / WITNESS_NOT_FOUND` within the unchanged scan bound. No later
generated ruleset, short game, Gate 3, or evolution ran. Gate 2 remains
harness-blocked and Gate 3 frozen.

Focused verification passed:

```text
pytest -q tests/test_gate2_merged_benchmark.py
4 passed
```

## Gate 2 optional-promotion applicability closeout

This in-place `CAUSAL_DIAGNOSTIC` derives promotion applicability from the
compiled contract: an allowed promotion pair is optional only when its target
is outside the corresponding type/owner forced-target set. Promotion is now
required only for rulesets with at least one such pair; the controlled
promotion witness and fixed-depth-1 search protocol are otherwise unchanged.

Western Chess reports no optional promotion semantics, so its promotion task
is `NOT_APPLICABLE` with reason `NO_OPTIONAL_PROMOTION_SEMANTICS`; all other
Chess capabilities passed. Standard Shogi reports optional promotion and found
a controlled witness with two favorable optional groups. Its unique global
one-ply best action was promoted; primary and reviewer both completed fixed
depth 1 in 95 nodes and selected it. Shogi promotion passed.

The merged benchmark continued and stopped at the next first failure: Shogi
`drop` under the existing raw any-drop expected set, with
`failure_type=HARD_FAILURE`. No generated ruleset, short game, Gate 3, or
evolution ran. Gate 2 remains failed and Gate 3 frozen.

Focused verification passed:

```text
pytest -q tests/test_gate2_merged_benchmark.py
4 passed
```

## Gate 2 controlled promotion-witness closeout

This in-place `CAUSAL_DIAGNOSTIC` replaced the raw "any promotion" expected
set with a controlled optional-promotion scan. Eligible states require only
nonterminal children, a same-source/same-target promoted/unpromoted pair with
strict promoted one-ply advantage, and an all-promoted global production
one-ply argmax that intersects a favorable pair. Accepted promotion decisions
would use fresh fixed-depth-1 primary/reviewer searches; no raw-promotion
fallback or 8,000-node cause check remains.

Within the unchanged deterministic 240-state/4-branch bound, Western Chess had
no eligible optional-promotion witness. Its existing hand-authored promotion
state is forced-promotion-only and therefore is not sufficient for this
capability. The task stops as `HARNESS_FAILURE` with reason
`CONTROLLED_PROMOTION_WITNESS_NOT_FOUND`; this is not agent weakness evidence.

All earlier Chess tasks still passed, including fixed-depth-3 mate-in-three
and fixed-depth-1 controlled material. The first stop is Chess `promotion`;
Shogi, generated rulesets, short games, Gate 3, and evolution did not run.
Gate 2 remains harness-blocked and Gate 3 frozen.

Focused verification passed:

```text
pytest -q tests/test_gate2_merged_benchmark.py
3 passed
```

## Gate 2 controlled material-witness closeout

This in-place `CAUSAL_DIAGNOSTIC` replaced the invalid first-positive-capture
eligibility rule inside the existing bounded capability scan. A material state
now qualifies only when every child is nonterminal, at least two captures have
positive values spanning at least two distinct values, and the max-value
capture set exactly equals the production evaluator's one-ply argmax. The old
8,000-node forced-continuation cause path was removed. No scan expansion,
fixture, standalone script/test, or production-code change was introduced.

The old Shogi `mate_one` material witness was rejected. The scan found a
controlled witness at `mate_three`: 41 legal nonterminal children and positive
capture values 189, 281, and 796. The unique value-796 capture was also the
unique one-ply evaluator best action. Fresh primary and reviewer searches both
completed fixed depth 1 normally in 83 nodes and selected that action; weak128
remained telemetry. Shogi `extreme_material` therefore passed.

The merged run continued and stopped at the next first failure: Shogi
`promotion` under the unchanged ordinary 1000-node primary budget. Its primary
did not choose the current promotion expected set, so classification remains
`RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_CAPABILITY` with
`failure_type=HARD_FAILURE`. No `drop`, generated ruleset, short game, Gate 3,
or evolution ran. Gate 2 remains failed and Gate 3 frozen.

Focused verification passed:

```text
pytest -q tests/test_gate2_merged_benchmark.py
3 passed
```

## Gate 2 Shogi extreme-material cause check closeout

This in-place `CAUSAL_DIAGNOSTIC` reused the existing deterministic Shogi
`extreme_material` witness, expected set, and 1000/128/8000-node root
decisions. Only after the primary missed the immediate-capture expected set,
the merged benchmark forced and equally reviewed the four expected actions
plus the one distinct primary/reviewer action. No legal-action sweep,
replacement witness, standalone script/test, games, generated rulesets,
Heavy job, learning, Gate 3, or evolution ran.
The synthetic witness's imported parent history could not be extended safely,
so every nonterminal forced child was normalized to the same fixed-child-root
history before continuation search; this mode is recorded in the result.

Result: `SHOGI_EXTREME_MATERIAL_EXPECTATION_NOT_VALIDATED`. The four expected
captures each had immediate rule value 1000 and used 8,000 review nodes; their
best continuation score was 3439. Primary1000 and reviewer8000 selected the
same non-capture, an immediate terminal win with forced-action score 999999999.
Thus no expected action reached the best compared score, and primary was not
below the best expected action. The immediate highest-capture rule is invalid
as search-level ground truth for this witness.

The task is now `HARNESS_FAILURE`, not agent `HARD_FAILURE`. The first stop
remains Shogi `extreme_material`; Gate 2 remains failed/harness-blocked and
Gate 3 remains frozen. No later task, ruleset, or short game executed.

Focused verification passed:

```text
pytest -q tests/test_gate2_merged_benchmark.py
3 passed
```

## Horizon-aware merged Gate 2 benchmark closeout

This `STRENGTH_BENCHMARK` corrected only the existing merged Gate 2 protocol.
Certified `mate_in_three` candidate and reviewer decisions now use fresh,
uncapped fixed-depth-3 searches; the 128-node weak control remains telemetry.
Every ordinary capability task retains 1000/128/8000-node budgets, and short
games retain those budgets plus the existing 10/20/30-ply half-weak criteria.
Per-decision action, node, depth, termination, and limit-mode telemetry is
recorded. All capabilities now run before any short game can start.

Chess passed every required capability. Its unique mate-in-three action was
`d4e5`; both candidate and reviewer completed depth 3 at 21,248 nodes and
selected it, while the weak 128-node control missed. Shogi mate-in-three also
passed at completed depth 3 (4,167 nodes candidate and reviewer). The run then
stopped at the first genuine failure: Shogi `extreme_material`, where the
unchanged 1,000-node candidate did not select an expected action.

Classification:
`RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_CAPABILITY`. No generated
ruleset or short game ran after that failure, and no Gate 3 work ran.
Gate 2 is explicitly `FAILED`; Gate 3 remains `FROZEN`.

Focused verification passed:

```text
pytest -q tests/test_gate2_merged_benchmark.py
3 passed
```

## Gate 2 mate-in-three exact node-threshold closeout

This bounded `CAUSAL_DIAGNOSTIC` used the same fixed Chess mate-in-three
position, production rule-derived evaluator, and deterministic Python
AlphaBeta configuration as the solving-horizon diagnostic. After the cheap
unique-forced-action reproduction assertion, exactly two fresh depth-3
searches ran, at node caps 21,248 and 21,249. No other budget, game, Arena,
Heavy job, learning, evaluator/search change, or Gate 3 work ran.

Result: `GATE2_MATE3_EXACT_MIN_NODE_CAP_21249`. At cap 21,248 the search hit
`node_limit` at 21,248 nodes, retained completed depth 2, and returned `c5c8`.
At cap 21,249 it completed depth 3 using 21,248 nodes and returned the unique
forced move `d4e5` with mate score 999999997. Thus the prior 1,000-node miss is
not evidence against evaluator capability; this certified tactical horizon
needs an explicit depth-3 guarantee or a node floor of at least 21,249.

Focused verification passed:

```text
pytest -q tests/test_gate2_mate3_exact_node_threshold.py
1 passed
```

## Gate 2 mate-in-three solving-horizon diagnostic closeout

This bounded `CAUSAL_DIAGNOSTIC` tested whether the corrected Gate 2 Chess
mate-in-three failure came from the 1,000-node cap preventing depth 3 or from
production AlphaBeta failing even after a complete depth-3 search. The unique
forced move was reproduced as `d4xe5` (`d4e5` in UCI), then exactly two fresh,
deterministic production searches were run without a node cap, at maximum
depths 2 and 3. Quiescence, ordering, transposition tables, disk cache, and
native legality were disabled. No games, tuning, Heavy job, or Gate 3 work ran.

Result: `GATE2_MATE3_FAILURE_IS_NODE_BUDGET_HORIZON_SHORTFALL`. Depth 2
completed after 831 nodes and chose `c5c8`; depth 3 completed after 21,248
nodes and chose the unique forced move `d4e5` with a mate score. Because depth
3 solved the position, the conditional exact-minimax control was not run.

Focused verification passed:

```text
pytest -q tests/test_gate2_mate3_solving_horizon_diagnostic.py
1 passed
```

## Mainline route reset closeout

The latest user instruction and Supervisor decision superseded and rejected
F154/F155. The authoritative route is now recorded in
`docs/architecture/GENERICCHESS_THEORY_ROADMAP.md` at checkpoint
`ea08d6cce46470bc901ff60859e5dac74725e0c5`: known-game Chess/Shogi algorithm
equivalence, then rule-prior baseline strength, then only conditional Gen0
evolution. No F154 work was completed or committed.

## F159 F158 policy-divergence microprobe closeout

F159 was a bounded `CAUSAL_DIAGNOSTIC` following F158's stalemate-dominated
neutral result. It reconstructed exactly the four F158 roots (initial and the
deterministic two-ply openings for seeds 15701 and 15702) and ran one fresh
depth-2 Python ABP search with the frozen rule prior and one with the exact
flat control on each root: eight searches total, with qsearch, ordering, TT,
and disk cache disabled. No games, new seeds, or deeper searches were used.

Result: `F158_POLICY_DIVERGENCE_EXISTS_BUT_STALEMATE_ERASES_OUTCOME_SIGNAL`.
The seed-15701 initial root diverged while the other three roots agreed; all
eight searches completed at depth 2. The probe records the two actions, root
scores, completed depths, legal-action count, and equality flag for every
root, plus both-evaluator child evaluations for the divergent root.

## F158 rule-prior versus flat-control micro-arena closeout

F158 was the bounded `STRENGTH_BENCHMARK` requested after F157. It reused
exactly generated seeds 15701 and 15702 and compared the frozen rule-derived
profile with an otherwise identical flat non-anchor profile. Search was fresh,
deterministic Python ABP at depth 2 with ordering, TT, and qsearch disabled.

The initial role-swapped pair on each ruleset was neutral, so the specified
second evaluator-neutral two-ply opening pair was run for each ruleset. All
eight games ended in ordinary stalemate draws; both rulesets remained neutral
at pair score 0.5. Classification: `RULE_PRIOR_BASELINE_STRENGTH_SIGNAL_INCONCLUSIVE`.
No further games, Heavy, or evaluator changes were authorized by F158.

Focused verification passed:

```text
pytest -q tests/test_f158_rule_prior_vs_flat_control_microarena.py
1 passed
```

## F157 rule-prior tactical sanity closeout

F157 was a bounded `CAUSAL_DIAGNOSTIC` with no games and no Heavy. The frozen
`EvaluationConfig()`/`build_ruleset_profile()`/production `Evaluator` was
tested on the first two valid minimal generated rulesets from seeds 15701 and
15702. Each had at least two non-anchor types with distinct rule-derived board
values. A deterministic witness finder placed one owner-0 attacker against a
HIGH and LOW target, with both captures legal and both children nonterminal.

Result: `RULE_PRIOR_TACTICAL_SANITY_PASS`. Both witnesses had positive
HIGH-minus-LOW material and full-evaluator differences; the HIGH capture was
the unique best one-ply full-evaluator child and the fresh depth-1 Python ABP
smoke search selected it. The probe stopped after two witnesses, used no
learned or hand-tuned values, and ran exactly two depth-1 searches.

Focused verification passed:

```text
pytest -q tests/test_f157_rule_prior_tactical_sanity.py
1 passed
```

## F156 known-game shallow-search equivalence closeout

F156 was a bounded `CAUSAL_DIAGNOSTIC`. The unknown was whether the existing
Python AlphaBeta and semantic Native paths agree on deterministic shallow
decisions when they receive the same fixed material-only evaluator. The probe
used four fixed roots: Western quiet/capture and checkmate positions, plus a
Standard Shogi drop/promotion/capture/material-choice position and a repeated
position. Full games were unnecessary because static child values, depths 1/2,
fresh repeats, and terminal categories directly observe the unknown.

Result: `KNOWN_GAME_SHALLOW_SEARCH_EQUIVALENCE_PASS`. Static material rows
matched for both rulesets; both search paths were deterministic at depths 1 and
2 and matched root scores, actions, and completed depths; no ordering tie
witness remained in the final roots. Western checkmate and Shogi repetition
both matched terminal outcome category.
The diagnostic and its contract test are in
`scripts/f156_known_game_shallow_search_equivalence.py` and
`tests/test_f156_known_game_shallow_search_equivalence.py`.

Focused verification passed:

```text
pytest -q tests/test_f156_known_game_shallow_search_equivalence.py tests/test_theory_roadmap_route_reset.py
2 passed
```

## F153 mutation root-sensitivity closeout

### Outcome

F153 completed as a bounded `CAUSAL_DIAGNOSTIC` with no games and no Heavy.
The question was whether F144's six sigma-0.35 mutation directions were large
enough to change fixed ABP root decisions. The first 4 positions were the two
F151-sensitive openings plus fixed evaluator-neutral seeds 1530101 and
1530102. Sigma 0.35 remained sparse through the 4-, 8-, and 12-position
limits. Reusing the same 12 positions, sigma 0.70 produced 3 changed
mutant-position roots, covering 3 mutants and 2 positions. Classification:
`SUFFICIENT_LEVERAGE`.

The smallest observed leverage scale was therefore sigma 0.70; sigma 1.40 was
not run. This is local mutation-to-search leverage only and makes no strength
claim.

### Evidence

- The initial batch was exactly 4 positions × 7 fresh evaluators = 28 root
  searches. Every search used fresh player/TT state, max_nodes 1000, depth 12,
  qdepth 4/8, fixed ordering, and the unchanged F144 material evaluator.
- The sigma-0.35 stages at 4, 8, and 12 positions were `SPARSE_LEVERAGE`,
  with one changed mutant-position root concentrated on F151 opening
  `742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c`.
- Sigma 0.70 changed roots for mutants 0, 3, and 4 across the two F151
  sensitive opening IDs. The result also contains the auxiliary one-ply
  material successor observations for the initial four positions.
- The artificial extreme-vector positive control changed the known F151
  opening-0 root action, while repeated Gen0 searches were identical under
  independent fresh TT instances.

### Verification

- Result artifact: `.generic_chess_flow/f153-shogi-material-mutation-root-sensitivity-result.json`
  (transient and ignored), generated from checkpoint
  `91d333b76d512c3b203d860c1d5a8865397dc89b`.
- F153 tests cover F144 sigma-0.35 parity, the NO/SPARSE/SUFFICIENT leverage
  classes, 4/8/12 limits, deterministic independent root searches, and the
  artificial extreme positive control.

### Routing

The next bounded experiment may use sigma 0.70 for the tiny shared-opening Gen1
screening described by Supervisor. F153 does not authorize a promotion or a
new evaluator feature.

---

## F151 paired-score microprobe closeout

### Outcome

F151 completed as a bounded, non-Heavy diagnostic using the frozen F149
score-race and fixed ABP/search contract. Stage A stopped after its initial 16
of 32 neutral openings because it found 2 Gen0-vs-M140 best-action
disagreements (2/16, 0.125). Stage B then tested exactly the first two
divergent openings as role-swapped F149 pairs. Both pairs were valid; their
pair scores were 0.5 and 0.0, respectively. Both role-swapped trajectories
were divergent. Classification:
`MATERIAL_VECTOR_PRODUCES_PAIRED_SCORE_DISCRIMINATION_MICROPROBE`.

The historical vectors matched exactly. Gen0 was
`(250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856,
240)` with SHA `b428c1e044d48587aa746aaea5aadc8646f0afbaf45be9c59f5d28342a724644`.
M140 was generated from seed 1440401 at sigma 1.40 with SHA
`3da16a8fdc92c268dcae7a11bfdfb88edfc073f411a4004336abace83ff1b177`.

Stage A's root-search score differences (M140 minus Gen0) had median 0 and
mean 4710; completed depths ranged from 1 to 2. The two Stage-B pair details
were:

- Opening index 0: both games valid score tiebreaks, pair score 0.5; game
  plies 122/62.
- Opening index 8: both games valid, pair score 0.0; the child lost both
  role-swapped outcomes (checkmate at 502 plies in one game and score
  tiebreak at 134 plies in the other).

### Verification and evidence

- Exact command:

  ```text
  .\\.venv\\Scripts\\python.exe scripts\\f151_shogi_material_paired_score_microprobe.py --output .generic_chess_flow\\f151-shogi-material-paired-score-microprobe-result.json
  ```

- Result artifact: `.generic_chess_flow/f151-shogi-material-paired-score-microprobe-result.json`
  (transient and ignored), created at 15:27:06.263 JST.
- Stage A used seed 1510101, opening range 16–32, and fresh independent
  players/TTs for each vector probe. No Heavy or evolution job was started.
- The implementation and focused tests cover the fixed search, vector parity,
  classification, trajectory hashing, and F149 score-race contract.

### Routing

This microprobe establishes behavioral paired-score discrimination for the
existing material vector without making a strength claim. Per the current
Supervisor/user authorization, the next step is the published F150 route with
its unchanged threshold-10 score race, 16–32-ply openings, and own
12-pair/3-non-0.5 discrimination gate. The historical F149 density result is
not a blocker for that authorized F150 run.

## F150 completed deep-opening discrimination/evolution closeout

### Outcome

F150 completed its registered Heavy run without intervention. The unchanged
threshold-10 deep-opening score race did not discriminate Gen0 from a material
diagnostic vector, so no Gen1 or Gen2 candidate was produced and nothing was
promoted. Classification:
`DEEP_OPENING_SCORE_RACE_INSUFFICIENT_MATERIAL_DISCRIMINATION`.

The run was `f150-deep-opening-evolution-v1-101bf96d1a84`, started at
2026-09-21 15:36:30.103 JST and completed at 20:14:07.003 JST, for
4 hours 37 minutes 36.900 seconds, with exit code 0. The result artifact was
`.generic_chess_flow/f150-deep-opening-evolution-result.json` and records the
tested checkpoint `83f4b062fe5e29f7764c80c7bc498541a4ee2c96`.

### Evidence

- The discrimination phase attempted 36 role-swapped pairs / 72 games; 12
  valid pairs remained and every pair scored 0.5, with mean 0.5 and bootstrap
  95% CI [0.5, 0.5].
- There were 36 invalid games (0.5), including 34 repetition endings and 2
  no-contest endings; 24 attempted pairs were invalid. Only 3 games reached
  the threshold, with zero formal Core decisive games.
- The F149 calibration embedded in the result remained consistent: 8 valid
  pairs / 16 valid games, 6 invalid games, and 4 threshold wins. Search,
  ordering, material-only evaluation, and score-race semantics were unchanged.

### Routing

This is a strength-benchmark failure, not project completion. Per Supervisor
direction, the next experiment is a bounded `CAUSAL_DIAGNOSTIC` root-sensitivity
probe of mutation-to-search leverage before any further full-game evolution.

## F150 deep-opening discrimination/evolution stop closeout

### Outcome

F150 was stopped by the Supervisor before its first discrimination wave
completed. The registered Heavy was active in Stage 1, the fresh Gen0-vs-M140
deep-opening discrimination run; no discrimination result was persisted and no
Gen1/Gen2 evolution stage started. The F150 result artifact is absent.

The exact registered run was
`f150-deep-opening-evolution-v1-d070c83a1bf9`. It was started at
2026-09-21 13:47:03.368 JST and stopped at 14:24:45.284 JST, for an elapsed
runtime of 38 minutes 41.916 seconds. Heavy status is `failed` with exit code
1 because the Supervisor intentionally terminated the process tree; this is
not an experiment failure and was not retried.

### Verification and preserved evidence

- Exact command:

  ```text
  .\generic-chess-flow.cmd heavy-start --label f150-deep-opening-evolution-v1 --resource-envelope .generic_chess_flow\f150-deep-opening-evolution-envelope.json -- .\.venv\Scripts\python.exe scripts\f150_shogi_material_score_race_deep_opening_evolution.py --output .generic_chess_flow\f150-deep-opening-evolution-result.json --workers 4
  ```

- Registered state, command, stdout, and stderr remain under
  `.generic_chess_flow/heavy-runs/f150-deep-opening-evolution-v1-d070c83a1bf9/`.
- No result artifact was created; no downstream screening, promotion, or
  evolution was run.
- The exact process tree was terminated and verified absent. No replacement
  Heavy or retry was started.

### Routing

F149 remains a failed pilot gate: invalid fraction 0.2727272727272727,
threshold/formal decisive fraction 0.18181818181818182, and all 8 retained
self-pairs scored 0.5. The next authorized work is a minimal analysis of why
paired role-swap scores remain 0.5, whether the score is distinguishable from
the material vector, and the smallest experiment that can test that question.
No large compute, threshold/weight/opening variant, or new score variant is
authorized until the Supervisor explicitly approves it.

# F149 deep-opening score-race Pilot A closeout

## Outcome

F149 restored the original threshold-10 score race and changed only the
evaluator-neutral opening depth to 16–32 plies. Pilot A obtained exactly 8
valid self-pairs but failed the density gate, so Pilot B and Gen1/Gen2
evolution were not run. Classification:
`SCORE_RACE_DEEP_OPENINGS_PILOT_FAILED_DENSITY`.

Across 11 attempted pairs / 22 games, 8 pairs / 16 games were valid and 3
pairs / 6 games were invalid. All invalid games ended by repetition. There
were 4 threshold wins, 12 score-tiebreak wins, zero formal Core wins, 152
capture events, 10 check events, and 162 total score events. The
threshold/formal decisive fraction was 0.18181818181818182, below the 0.50
gate; the invalid-game fraction was 0.2727272727272727, above the 0.25 gate.
Valid-game plies had median 170.5, p90 455, and maximum 500. Threshold plies
were 94, 94, 455, and 455. The self-pair mean was exactly 0.5, but every
retained pair score was 0.5, so no material discrimination was established.

The deep openings increased event activity substantially versus shallow
calibrations and produced 12 unequal-score tiebreak outcomes, but did not
produce enough threshold/formal decisive outcomes to meet the work-order
fitness gate.

## Verification and operational note

- Exact command:

  ```text
  .\generic-chess-flow.cmd heavy --resource-envelope .generic_chess_flow\f149-score-race-deep-openings-envelope.json -- .\.venv\Scripts\python.exe scripts\f149_shogi_material_score_race_deep_openings.py --output .generic_chess_flow\f149-score-race-deep-openings-pilot.json --workers 4 --pilot-only
  ```

- Result artifact: `.generic_chess_flow/f149-score-race-deep-openings-pilot.json`
  (transient and ignored), completed at approximately 13:36:53 JST after
  about 76 minutes. It records tested checkpoint
  `95f65b533956b4ffe91b50b497912904f5557996`.
- The fixed material evaluator/search stack and evaluator-independent scoring
  were preserved; F149 tests plus F148/F146/F145/F144/Search regression tests
  passed: 43 tests.
- Post-run `heavy-status` contained no F149 `heavy-runs` record even though
  the child ran through `generic-chess-flow.cmd heavy`. The minimal correct
  usage for any future long run is the registered form
  `generic-chess-flow.cmd heavy-start --label <label> --resource-envelope <path> -- <command>`;
  no replacement or rerun is authorized for F149.

## Routing

Per Supervisor direction, stop at Pilot A. Do not run discrimination or
evolution, and do not alter threshold, weights, evaluator, or search to
rescue this result. The next work order must reconsider the score-race
fitness definition after the shallow threshold-10, shallow capture-five, and
deep-opening threshold-10 calibrations.

---

# F148 capture-five score-race Pilot A closeout

## Outcome

F148 kept the authorized threshold 10 and check +1, changing only non-anchor
capture reward to +5. Pilot A obtained exactly 8 valid self-pairs but failed
the density gate, so Pilot B discrimination and Gen1/Gen2 evolution were not
run. Classification: `SCORE_RACE_CAPTURE5_PILOT_FAILED_DENSITY`.

Across all attempted replacements, the pilot evaluated 54 pairs / 108 games:
8 valid pairs / 16 valid games and 46 invalid pairs / 92 invalid games. All
92 invalid games ended by repetition. The 16 valid games all ended by score
threshold, with no score-tiebreak or formal Core wins. Capture events totaled
58, checks remained zero, and total race points were 290. Threshold plies had
median 19, p90 41, and maximum 94; valid-game plies had median 19, p90 41,
and maximum 94. The self-pair mean was exactly 0.5. The invalid-game fraction
was 0.8518518518518519, and threshold/formal decisive fraction was
0.14814814814814814, both failing the required gates.

## Verification and routing

- Result artifact: `.generic_chess_flow/f148-score-race-capture5-pilot.json`
  (transient and ignored).
- The artifact records tested checkpoint
  `cc7a2627e107f0598815243ecb22dd7667bbe704`; local and `origin/sandbox`
  SHAs matched.
- F148 direct plus F146/F145/F144/Search regression tests passed: 39 tests.
- The fixed F144 material evaluator, ordering, ABP/search budget, TT, and
  evaluator-independent scoring were preserved.

Because capture-five still leaves the score race repetition-dominated and
below the decisive-density gate, no further weight change is made inside F148.
The next route requires a new explicit work order; no ordinary full-game
validation is justified.

---

# F147 threshold-1 diagnostic route correction

## Outcome

F147 threshold-1 code and tests were published as a diagnostic checkpoint,
but the requested Heavy pilot was stopped by the active Supervisor before it
could produce a result. The run was explicitly `--pilot-only`; it never
entered discrimination or evolution, and no threshold-1 acceptance claim is
made.

Exact command:

```text
.\generic-chess-flow.cmd heavy --resource-envelope .generic_chess_flow\f147-score-race-threshold1-envelope.json -- .\.venv\Scripts\python.exe scripts\f147_shogi_material_score_race_threshold1_evolution.py --output .generic_chess_flow\f147-score-race-threshold1-pilot.json --workers 4 --pilot-only
```

The four-worker run started at approximately 11:15:08 JST and was stopped at
approximately 11:22:17 JST after progressing through replacement waves. No
result artifact was written, so completed-game and CPU totals are not claimed;
the observed wall time was about seven minutes. The published diagnostic
checkpoint is `25ed8fc93e9992ab4e4c61d53102f81b06b885ba`, with 40 targeted tests
passing and local/remote SHA parity.

## Mainline routing

The threshold-1 work order is superseded and must not continue. Return to the
user-authorized score-race route: threshold 10, capture +1, check +1,
capture+check +2, formal Core precedence, unequal nondecisive terminal scores
resolved by the restored tiebreak, and equal scores invalid. F145/F146 showed
zero check events, sparse captures, and repetition-dominated termination;
threshold lowering is not an authorized substitute for diagnosing that
fitness surface. The next step requires the smallest explicit scientific
correction on that route, followed by a targeted pilot before any evolution.

---

# F146 threshold-3 score-race diagnostic closeout

## Outcome

F146 was run in pilot-only mode after the Supervisor-directed route restored
the user-authorized terminal rule: first reach score 3, formal Core decisive
outcomes take precedence, and for repetition/max-ply/non-contest terminals an
unequal race score is the winner while equal scores are invalid. The pilot
failed its acceptance gate, so no Gen1/Gen2 evolution or full-game validation
was started. Classification:
`SCORE_RACE_THRESHOLD3_PILOT_FAILED_ACCEPTANCE`.

The strict threshold-3 diagnostic first produced 32 attempted games, all
invalid repetition terminals, with 26 capture points and no check points. The
restored tiebreak pilot produced 32 attempted games across 16 pairs: 2 valid
score-tiebreak games and 30 invalid repetition games, giving an invalid-game
fraction of 0.9375. The single valid pair tied at 0.5; it had 26 capture
points, zero check points, zero threshold wins, zero formal decisive games,
and a median valid length of 129 plies. The self-pair mean was exactly 0.5.
The score-race signal therefore remains too sparse and repetition-dominated
to justify evolution.

## Implementation and verification

- Published and tested checkpoint: `ee5426295e651cf0aa19885cb52764159f9935b6`.
- The tiebreak artifact records that exact `git_sha`; `HEAD` and
  `origin/sandbox` were verified equal at that SHA.
- F146 schema is `F146_SHOGI_MATERIAL_SCORE_RACE_V2`, with capture +1,
  check +1, capture+check +2, threshold 3, and score independent of material
  values. The fixed F144 material evaluator and search stack were preserved.
- Required targeted tests passed: 34 tests covering F146, F145, F144, and
  AlphaBeta search behavior.
- Both pilots used fresh role-swapped paired openings and four process
  workers. Result artifacts and envelopes remain transient under
  `.generic_chess_flow/`.

## Routing

The strict and restored-tiebreak diagnostics both fail to establish useful
behavioral fitness. Per the active Supervisor route, no threshold reduction,
complex learner, search expansion, or full evolution was started. The next
step requires a new explicit work order or route decision.

---

# F145 score-race pilot closeout

## Outcome

The user-authorized Standard Shogi score-race pilot completed in pilot-only
mode and did not meet the acceptance gate, so full Gen1/Gen2 evolution was not
started. Classification: `SCORE_RACE_PILOT_FAILED_ACCEPTANCE`.

The pilot used fresh role-swapped pairs, fixed F144 material evaluation and
search, capture +1, check +1, capture+check +2, first to 10, and 512 plies as
the safety bound. The four valid games had 30 capture points, zero check
points, median 133.5 plies, and repetition terminal causes. No game reached
the score threshold or a formal decisive Core outcome; accepted signal
fraction was 0.0. The conservative shortness check `median_plies < 250`
passed, but the behavioral fitness gate failed. The initial run also exposed
that replacement accounting eagerly evaluated the full pool; the published
implementation now evaluates the target opening wave first and consumes
fresh openings only for invalid equal-score replacements.

## Scope and verification

- F145 Heavy was safely stopped before its superseded full-game diagnosis and
  left no result artifact; only its transient envelope was removed.
- The score-race pilot Heavy used four process workers and wrote transient
  evidence to `.generic_chess_flow/f145-score-race-pilot.json`.
- The score-race implementation keeps F144 `MaterialOnlyEvaluator`, ABP,
  ordering, quiescence, TT, and limits unchanged; score points are independent
  of material values and formal Core decisive outcomes take precedence.
- Tests passed: 33 targeted F145/F144/Search tests.

## Routing

Because the pilot did not produce threshold or formal-decisive signal, no
full evolution or promotion was authorized. Any next run must adjust only the
score-race threshold/event weights through Chat; no learner or search-stack
expansion is justified by this pilot.

---

# F144 closeout

## Outcome

F144 completed its required fresh Standard Shogi material-only Arena attempt
with classification `MATERIAL_ONLY_GEN1_DOES_NOT_BEAT_GEN0`. Gen1 did not
promote, so the required Gen2 comparison was not run. This is a benchmark
failure to establish improvement, not a project-level completion.

## Implementation and evidence

- Tested and published checkpoint: `cb1f93d035f0584db6215602b561afd9362be18c`.
- The result artifact was generated from that exact checkpoint; its
  `git_sha` is `cb1f93d035f0584db6215602b561afd9362be18c`.
- Search was fixed at max_nodes=1000, max_depth=12, quiescence depths 4/8,
  TT 250000, `SearchTuning()`, fresh player per game, and one frozen
  rule-derived ordering table.
- Integrity check: 4 paired screening games, 8 draws, mean pair score 0.5,
  bootstrap 95% CI [0.5, 0.5], no no-contest games.
- Gen0 vector seed was 1440201 with canonical median 1000. Gen1 evaluated six
  mutants using the required screening schedule; all six tied the parent at
  mean pair score 0.5. The selected mutant was index 0.
- Fresh promotion: 24 paired comparisons (48 games), 47 draws and one
  explicit no-contest game. The no-contest pair was retained as non-scoring,
  not converted to a draw; 23 scoring pairs tied at mean 0.5 with bootstrap
  95% CI [0.5, 0.5]. Promotion was false.
- The result artifact reports no wins or losses in either screening or
  promotion. Raw traces remain transient as required.

## Tests

The F144 test suite and existing AlphaBeta search tests passed after the
no-contest handling fix: 24 F144 tests plus the existing search tests.

## Follow-up

The current evidence does not justify adding a more complex learner. A later
rerun, if ordered, should first apply the recorded efficiency correction:
replace CPU-bound thread parallelism with true process-based parallelism and
add resumable per-generation/per-candidate checkpoints while preserving
deterministic openings and result semantics. The current completed run was not
interrupted or restarted.

---

# Gate 1 known-game backend equivalence closeout

## Outcome

Supervisor route correction completed the requested `CAUSAL_DIAGNOSTIC` Gate 1
before any Gate 2 work. The benchmark passed and stopped at no hard fork.

## Implementation and evidence

- Added `scripts/gate1_known_game_backend_equivalence.py`, a benchmark-only
  common negamax/alpha-beta harness using fixed material values and canonical
  action ordering.
- Compared GenericChess Western Chess against `python-chess` on 12 fixed
  positions at depth 2 and 4 fixed low-branch positions at depth 3.
- Compared GenericChess Standard Shogi against `cshogi` on 12 fixed positions
  at depth 2 and 4 fixed low-branch positions at depth 3.
- Each row records legal actions, terminal result, static material, best move,
  root score, PV, nodes, wall time, and nodes/second for both backends.
- All compared search tuples matched exactly, including node counts. The
  production `AlphaBetaPlayer` sanity returned legal actions for both games.
- Raw benchmark JSON remained transient and was not added to Git.

## Tests

- `tests/test_gate1_known_game_backend_equivalence.py` passed.
- The targeted production suites passed: 37 tests covering Gate 1, AlphaBeta
  search, Standard Shogi product behavior, and Western Chess product behavior.

## Routing

Gate 1 is complete. Gate 2 was not started, as required by the Supervisor.

---

# Gate 2 R1 forced-win microbench closeout

## Outcome

`STRENGTH_BENCHMARK` completed on the exact F86O/F86Q frozen generated
ruleset and root. The F86O policy tape replay reconstructed root digest
`48cdc72b8ca6551f2a5cc0bd3b5c4aec6e05aa49a602c7436a22f49f59728114` at ply
10 with seat assignment `B/A`; the ruleset fingerprint matched
`29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff`.

## Observation

- The normal rule prior had P0/P1 values `1095/905`; the flat control used
  ordinary value `1000`, hand value `900`, and zero promotion gains.
- Exactly two production Python AlphaBetaPlayer root searches ran, both at
  depth 2 with qsearch 0/0, TT off, ordering off, disk cache off, native
  legality off, and deterministic fresh players.
- The flat control selected the certified action `[3,4] -> [2,3]` with the
  certified action digest; the rule prior selected a different action.
- Because the rule prior did not select the certified action, the conditional
  conversion trials were not run. Classification:
  `GATE2_R1_POLICY_DIVERGENCE_WITHOUT_WINNING_ROUTE`.
- No production search, evaluator, rules, generator, or learning code was
  modified. No full games, Heavy job, Arena, random scan, or bootstrap ran.

## Tests and routing

- Added the bounded replay/search regression test; it passed together with the
  Gate 1 test and the existing targeted production suites.
- This witness is a non-winning policy divergence, so no second witness was
  started in this turn; the next route remains governed by Chat's follow-up.

---

# Gate 2 R2 selected-action forced-win check closeout

## Outcome

The exact R1 decision reproduction passed on the frozen ruleset/root. An
evaluator-free three-ply terminal tree then checked only the certified action
and the rule-prior-selected action.

## Observation

- The certified F86Q action `[3,4] -> [2,3]` has two legal opponent replies;
  each has one owner-0 mating continuation, so
  `FORCED_MATE_WITHIN_3_PLIES=true`.
- The rule-prior-selected action has eight legal opponent replies; every reply
  has zero owner-0 mating continuations, so it is not a forced win within the
  same horizon.
- Classification: `RULE_PRIOR_TACTICAL_COUNTEREXAMPLE_CONFIRMED`.
- No evaluator scores were used by the predicate, and no full games, deeper
  AlphaBeta, Heavy, Arena, new rulesets, or production changes were made.

## Tests and routing

The R2 regression test passed. This closes the ordered Gate 2 R2 diagnostic;
the next requested causal diagnostic should inspect only the competing root
actions and identify which rule-prior term causes the wrong depth-2 ordering.

---

# Gate 2 R3 forced-win horizon disambiguation closeout

## Outcome

R3 reconstructed the same frozen root and profiles without rerunning R1/R2
depth-2 searches, then ran exactly two fresh depth-3 production searches.

## Observation

- Both the rule prior and flat control completed depth 3 and selected the
  certified F86Q action `[3,4] -> [2,3]`.
- The existing evaluator-free exact predicate confirmed that action forces
  owner-0 checkmate within three plies.
- Classification: `GATE2_DEPTH2_COUNTEREXAMPLE_IS_HORIZON_LOCAL`.
- The R2 depth-2 divergence is therefore horizon-local for this witness; it
  does not justify changing P0/P1 or decomposing rule-prior terms from this
  root.
- No full games, Arena, Heavy, new ruleset, or production changes were made.

## Tests and routing

The R3 regression test passed. Per the work order, the next diagnostic should
move to a second already-published generated tactical witness at its minimum
solving depth; evaluator tuning remains frozen.

---

# Gate 2 R4 independent mate-in-two witness closeout

## Outcome

R4 used only the frozen F86N-R1 V4-3 ruleset and first F86S V4-3 witness
`T0075`, then deterministically checked 119 relocation candidates to find the
first nontrivial ongoing root with six legal actions, one exact forced-mate
action, and five non-forced actions. The source fingerprint and exact-checkmate
validation matched the published authority.

## Observation

- Exactly two depth-2 and two depth-3 production searches ran with the
  prescribed fresh-player, qsearch 0/0, TT/order/native/disk-off settings.
- At depth 2, both rule prior and flat control selected a non-forced action.
- At depth 3, both selected the unique forced-mate action, and both passed the
  evaluator-free solving control.
- Classification: `GATE2_R4_NEITHER_GUIDED_TO_WINNING_ROUTE`.
- This witness provides no shallow guidance conclusion; no games, Heavy,
  training, scan beyond the 256-candidate bound, or production changes ran.

## Tests and routing

The R4 regression test passed. Per the work order, this is not a rule-prior
positive or negative signal; Gate 2 remains open pending Chat's next route.

---

# Gate 2 merged benchmark closeout (superseded)

## Comprehensive conclusion

The earlier merged entry reused insufficient microchecks and was later
invalidated by the Supervisor. Its PASS and supporting counts must not be used
as Gate 2 evidence.

Classification: superseded.

The corrected single entry below replaces this conclusion; no fragmented R5/R6
scripts, fixtures, schemas, or production changes were added.

---

# Gate 2 corrected merged benchmark closeout

## Comprehensive conclusion

The directly corrected single entry now uses real directional states and
expected actions, Chess/Shogi plus five fixed generated rulesets, initial and
fixed shallow-opening role swaps, a 128-node weak ABP, and 8000-node
action-score review with normalized regret, forced-mate misses, obvious-error
rate, exact half-weak thresholds, and 10/20/30-ply observations. The run
stopped at its first real hard failure.

Chess mate-in-1 passed. On a distinct strict mate-in-3 state, the unique
forced action was `d4xe5`; the 1000-node candidate selected `Rc8`, the
128-node weak control selected `Qxf5`, and the 8000-node reviewer also selected
`Rc8`. The first failure was therefore Chess `mate_in_three`, and the result
was:
`RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_CAPABILITY`.

The required early stop means no short games or later rulesets were executed;
no Gate 3 conclusion is supported. Gate 3 remains frozen, and its published
R1/R2 commits remain historical invalid-route diagnostics only.

## Verification

- The existing merged regression file checks the exact tactical failure,
  reviewer-score regret normalization, and exact half-weak threshold.
- The transient corrected result remains ignored under
  `.generic_chess_flow/gate2-corrected-v2-result.json`.

---

# Gate 3 R1 rule-prior contrast leverage closeout

## Classification

`GATE3_RULE_PRIOR_CONTRAST_NO_LOCAL_LEVERAGE`

The diagnostic used the frozen F86Q F/V5-3 ruleset
`29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff` and
exactly three published F86Q roots: the Gate 2 R1/R3 root, followed by the
first two different F/V5-3 roots in published selected-root order. The
checkpoint-backed Gen0 matched the production evaluator exactly at every root
and every legal one-ply child.

The requested symmetric material-contrast mutations `c=0.75` and `c=1.25`
changed none of the three 1000-node actions, so the prescribed wider
mutations `c=0.50` and `c=1.50` were also tested; they likewise changed none.
The run used 15 searches total, with no games, Arena, self-play, Heavy, or
production changes. The next route is one other single generic parameter
family, preferably mobility, using the same tiny leverage diagnostic.

## Validation

The Gate 3 R1 regression test passed. The published sandbox checkpoint is
recorded in the Courier closeout report.

---

# Gate 3 R2 mobility leverage closeout

## Classification

`GATE3_MOBILITY_NO_LOCAL_LEVERAGE`

R2 reused the Gate 3 R1 frozen ruleset, three F86Q roots, checkpoint-backed
Gen0, and deterministic 1000-node search settings. The deterministic Gen0
checkpoint identity guard matched
`0d71bf4f9385820bf30fc905a65c6456d70ad7c4c4f90c3809729853eaa38c1d`.

Neither primary mobility mutation (`1`, `3`) changed any root action. Per the
pre-registered bounded route, wider values (`0`, `4`) were then tested and
also changed no root action. The run used 15 searches total; no games,
Arena, self-play, Heavy, or production changes ran. Numeric score changes
without action changes were not treated as leverage.

## Validation and routing

The Gate 3 R2 regression test passed. The next diagnostic is the remaining
simple production dynamic family, `anchor_safety`, using the same small
causal-leverage procedure.

---

# Previous F142 closeout

- Work order: `GENERICCHESS_F142_CORRECTED_SHOGI_ACTION_DELTA_FACTORIZATION`
- Baseline: `576a14430b512a15f90e1368f59263ab3334e989`
- Scope: exact corrected action-conditioned transition-delta positive control using F141 shards; no new states, malformed F129 shards, semantic-action features, deeper search, self-play, MCTS, Adam, hidden layers, Arena, or production integration.
- Corrected oracle SHA: `fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6`.
- Feature-name SHA: `6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942`.
- Heavy runtime: `4918.114059686661` seconds.
- Result artifact: `.generic_chess_flow/f142-corrected-shogi-result.json` (ignored transient evidence).

## F141 reproduction and action representation

- Verified `F141_CORRECTED_T1_LABEL_SHARD_V1`, roots `3109/731/750`, action rows `200747`, unique child identities `200678`, duplicate-child reuse `69`, and F141 static T1 holdout nRMSE `1.8302864928571427`.
- Used exact root-perspective transition delta `Δφ(s,a) = -φ_child - φ_root`, raw width `1086`.
- Weighted train action target mean `107.7401908399005`, target std `427.56114655941656`; active width `1029`, constant width `57`, design width `1030`, numerical rank `1017`, nullity `13`, retained-spectrum condition number `22.234849323810053`.
- Effective ranks at `1e-6`, `1e-8`, `1e-10`: `1017`, `1017`, `1017`.

## Algebraic and identifiability controls

- Exact oracle recomposition passed: maximum absolute error `2.014388655879884e-12`, RMS `2.0115462024290702e-13`, failing rows `0`.
- Exact oracle null contribution normalized by holdout A1 std: train `1.75571742793859e-15`, dev `0.000454089917943636`, holdout `0.002446231891826169`.
- Train-constant delta-coordinate contribution normalized by holdout A1 std: train `0`, dev `1.116497812965183e-06`, holdout `7.5731511863142996e-06`.
- Both unavailable-component holdout contributions exceed `1e-8`; the action training surface is therefore non-identifiable for exact oracle prediction outside train.

## Weighted learner and action control

- Numerical gate passed: relative residual `9.835372490257463e-13`, objective excess `-1.0587911840678754e-22`, PCG-vs-ridge holdout nRMSE `1.8942955076102532e-10`.
- Weighted action holdout: RMSE `3.7120698649989774`, nRMSE `0.002453409540534049`, R² `0.9999196460358367`, Pearson `0.9999598431009133`, Spearman `0.9993652994551719`.
- Action gate passed: holdout top-1 `0.9986666666666667`, pairwise ordering `0.997758463607572`, normalized mean regret `0`, top-3 containment `1.0`, mean reciprocal rank `0.9993333333333333`.
- Max-pooled T1 holdout: RMSE `7.1560331655376395`, nRMSE `0.004729620044668247`, R² `0.9999776306942331`, Pearson `0.9999889683955635`; T1 gate passed.
- Relative RMSE reduction versus F141 static compressor: `0.9974159127201528`; versus root V* baseline: `0.9953667774005267`.
- F140 learned-value base shadow holdout RMSE `7.169132533773157`, nRMSE `0.004738277779078641`.
- Matched-ridge parameter diagnostics: row-space projection distance `2.4426415300978495e-05`, projected cosine similarity `0.9999999997418058`.

## Classification and routing

`F142_ACTION_DELTA_TRAINING_SURFACE_NONIDENTIFIABLE`

The exact transition-delta representation is algebraically correct and learns
action ordering and max-pooled T1 accurately, but the present action surface
exposes nonzero exact null and train-constant contributions on holdout. Per the
work order, this blocks interpreting the fit as an identifiability-complete
positive control. F129-F134 malformed-oracle conclusions remain quarantined;
F135-F141 corrected-oracle evidence remains valid. The action training surface
must be coverage-repaired before treating this as a definitive factorization
result.
