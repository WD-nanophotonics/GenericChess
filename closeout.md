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
