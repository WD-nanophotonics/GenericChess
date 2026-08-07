# Learning Phase 1.5: Arena Measurement Integrity + Clean Learning-Signal Verification

## Why the old arena measurement was unreliable

Learning Phase 1's arena had five measurement-contamination problems:

1. Every pair started from the same initial position (`ArenaConfig.seed` never
   influenced the position).
2. The parent/child `NativeSearchEngine` objects were created once for the
   whole arena, so TT entries persisted across games (cross-game TT
   contamination).
3. A "game" was not an independent sample: 20 games over one repeated
   position with warm TT are not 20 independent, identically-conditioned
   samples.
4. Engine failures (`result.action is None` on an ongoing position) were
   silently counted as draws.
5. The Wilson interval was applied to win/draw game scores instead of a
   paired metric, and `training_config_hash` was computed from a
   pre-calibration config that did not contain the actual calibrated alpha.

Consequently the earlier R2 numbers (0.55 / 0.60 / 0.70) are treated as
exploratory, not as audited evidence.

## Evaluator-neutral opening corpus

`generic_chess/learning/openings.py` builds `ArenaOpeningCorpus` from Core
legal actions only (GameSession + a local deterministic PRNG), with a stable
canonical action ordering (serialized action dicts) and seeded uniform choice
(2–6 plies, terminal openings rejected with deterministic retry). The corpus
ID is `stable_sha256(canonical payload)`; it is checkpoint-independent by
construction (the generator never touches an evaluator), serializable, and
replay-validated (fingerprint, legality, position keys, ongoing status).
For this proof one 16-opening R2 corpus (seed `314159`) is generated once and
shared by all training seeds as a fixed holdout set.

## Fresh-engine policy

Each arena game replays the corpus opening and creates **fresh** parent and
child engines, so TT never crosses games (a pair's two color-swapped games are
the only place TT can warm within one game). The `test_fresh_engine_per_game`
test instruments the engine factory and asserts `4 × pairs` engine creations.
Engine failures raise `ArenaExecutionError` instead of becoming draws.

## Pair statistics

`ArenaPairResult.child_pair_score = (game_child_owner0.points +
game_child_owner1.points) / 2`. The primary metric is the mean paired score
over the corpus with a **pair-level bootstrap** CI (10,000 resamples, seed
271828) in `generic_chess/learning/statistics.py`. Wilson is no longer used
as primary uncertainty; game-level W-D-L remains descriptive.

## Provenance

Experiments now write, in order:
1. `pre_calibration_config.json` (the frozen calibration rule, before any
   self-play),
2. `calibration.json` (trajectory ids, measured nominal L2, derived
   calibrated alpha, clamp flag),
3. `final_config.json` / `config.json` (all actual training parameters,
   including `calibrated_alpha`, `calibration_artifact_hash` and
   `opening_corpus_id`) and `training_config_hash =
   stable_sha256(final_training_config)`.

Checkpoints use schema v2 and carry that exact hash (asserted for every
generation).

## Corrected proof protocol

* RuleSet: R2 weird-generic 4×4.
* Opening corpus: 16 openings, seed `314159`, 2–6 plies, generated once,
  reused by all seeds.
* Training seeds: 7, 8, 9; 3 generations each; 8 self-play games/generation
  at 2000 nodes/move; `epsilon=0.10`.
* Alpha calibration unchanged: `target_l2_fraction=0.10`,
  `max_multiplier=200×nominal`.
* Arena: 16 pairs (32 games)/generation at 4000 nodes/move, fresh engines,
  paired color swap, no exploration.
* Gates before the proof: Gen0-vs-Gen0 (every pair exactly 0.5), reverse
  complement, deterministic rerun.

## Results

Corrected R2 proof (16 paired openings, seed 314159, fresh engines, 3
training seeds × 3 generations):

| seed | generation | pair mean | bootstrap CI | better/tied/worse | game W-D-L | weight L2 |
| --- | ---: | ---: | --- | --- | --- | ---: |
| 7 | 1 | 0.500 | [0.5, 0.5] | 0/16/0 | 16-0-16 | 40.1 |
| 7 | 2 | 0.500 | [0.5, 0.5] | 0/16/0 | 16-0-16 | 39.7 |
| 7 | 3 | 0.500 | [0.5, 0.5] | 0/16/0 | 16-0-16 | 39.3 |
| 8 | 1 | 0.500 | [0.5, 0.5] | 0/16/0 | 16-0-16 | 48.9 |
| 8 | 2 | 0.500 | [0.5, 0.5] | 0/16/0 | 16-0-16 | 32.9 |
| 8 | 3 | 0.438 | [0.344, 0.500] | 0/14/2 | 14-0-18 | 32.5 |
| 9 | 1 | 0.500 | [0.5, 0.5] | 0/16/0 | 16-0-16 | 23.0 |
| 9 | 2 | 0.500 | [0.5, 0.5] | 0/16/0 | 16-0-16 | 23.0 |
| 9 | 3 | 0.500 | [0.5, 0.5] | 0/16/0 | 16-0-16 | 23.0 |

Every game is decided by the first player (owner 0) regardless of the
checkpoint; the paired color swap neutralizes this, so all pair scores are
exactly 0.5. Material weight changes (L2 ≈ 23–49 per generation) never flip
an outcome on the diverse corpus. The earlier Phase 1 numbers
(0.55/0.60/0.70) are therefore **not reproduced** under the audited
protocol.

## Verdicts

* **Measurement: VALID** — Gen0-vs-Gen0 gate passed (16/16 pairs exactly
  0.5), reverse-complement and deterministic-rerun tests pass, fresh engines
  per game, paired diverse openings.
* **Learning signal: NO_POSITIVE_SIGNAL** — Gen1 positive seeds = 0/3 (all
  pair means exactly 0.5).
* **Stability: STABLE** — no generation collapsed below 0.25; the only
  non-0.5 result is seed 8 gen 3 at 0.438. (Vacuous: there is no signal to
  be stable about.)

Conclusion: under a clean, independent, same-budget paired measurement, the
Learnable-Material + TDLeaf pipeline shows **no reproducible positive
playing-strength signal** in this experiment.
