## Mainline route reset closeout

The latest user instruction and Supervisor decision superseded and rejected
F154/F155. The authoritative route is now recorded in
`docs/architecture/GENERICCHESS_THEORY_ROADMAP.md` at checkpoint
`ea08d6cce46470bc901ff60859e5dac74725e0c5`: known-game Chess/Shogi algorithm
equivalence, then rule-prior baseline strength, then only conditional Gen0
evolution. No F154 work was completed or committed.

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
