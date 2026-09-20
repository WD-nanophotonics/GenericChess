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
