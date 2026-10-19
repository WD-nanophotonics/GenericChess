# Task 2602 — standard-Chess learner path map

## Finding

The existing research code already has a standard-Chess execution route suitable for a bounded TD experiment: task2565's trainer dispatches generator seed 0 to ChessEnv and Model, replays Chess move histories through python-chess, and uses the same TDLeafEpisode update as the Generic domain. This makes a standard-Chess pilot an engineering task, not a requirement to build a new engine.

## Reviewed mechanics

- ChessEnv exposes five white-minus-black material-count features P/N/B/R/Q, fixes pawn weight P=1, and omits kings from the material vector. The Model uses a fixed tanh(material/10) transform, holds the fixed coordinate at one, and supplies the semi-gradient.
- Task2492's AlphaBeta search explicitly avoids material-based ordering, SEE, MVV-LVA, null move, futility and TT. Legal actions are permuted by a seeded RNG independent of coefficients; terminal leaves use actual environment outcomes. TreeStrap transforms search intervals and applies one-sided interval loss, not exactified alpha-beta bounds.
- The current trainer uses task2504.TrainingSearch and task2492.TDLeafEpisode. TrainingSearch returns the shared Receipt/Sample types with bounded search targets and incomplete-query rejection. It is a fixed-depth heuristic target, not an exact WDL solver; tactical-horizon cutoffs are counted as such.
- ChessEnv's terminal policy claims available threefold/50-move draws using the full move stack. This is a pinned policy choice and belongs in any comparison manifest.
- The trainer supports Chess, but it does not currently select TreeStrap as a trainer update. TreeStrap's learner update exists as a reusable method; a faithful end-to-end TreeStrap arm would need a separately frozen loop and total-cost accounting.
- The unregistered task2593 proposal is a narrow terminal-target eligibility-trace probe against ordinary TD(lambda=.95), not a faithful historical Beal–Smith or TreeStrap reproduction. It reuses old frozen Chess endpoints and proposes fresh root families, but its root-selection plan should be aligned to task2601's explicit finite-panel protocol before any future registration.

## Validation

Command: python from DEV_AUX's existing .venv, pytest -q on task2492/test_learning.py and task2492/test_episode.py with import-mode=importlib. Result: 13 passed. Exact output is in focused-tests.txt. This only validates learner/update contracts, not training convergence or playing strength. The unregistered task2593 candidate episode also passes its four focused tests (see task2593-tests.txt); this still does not register or run that candidate.

## Source pins

- task2492/learning.py — 88e7f08c0ce2ced7ab7ab9ca53036365bc6c53397db182d173684a194a6c25df
- task2492/episode.py — c1798654adbad62dbd8ddbcba836ac05469b0c7f99ee7db1b9f9f34303daa0e0
- task2492/adapters.py — 9d91ecd69308d79ff2a257a4addb79c7c6b91f67ec72e5e4173bbf02b4c7955f
- task2565/train.py — 38ff56df922a9d9e590d7d6502f051adfbddd379d8fed1fff85bc2a732b66f7d
- task2504/search.py — a3035830a4e6591bda2ce759540f53b3b184d3a0af41b6754dd35db04c522a69
- task2593/design.json — ab089eb1cfc73ac1b6432c68dfa02a72048143a48712ef8e37e4c288bb0685ad
- task2593/episode.py — 9e5449e87972ee4a46df7ba3c3a2a96310e77cae2553980447296fb3636abc9e
- task2593/test_episode.py — 58714b59aa826bdd5abeb58857ba389a662cc456e0edaab99fa1256cb87d05ff

At the time of this source-map checkpoint, no new training/evaluation run had started and the generic-transfer claim remained OPEN. Later task2594 registered and completed the finite Chess comparison; see docs/operations/COLLABORATION_LOG.md for its bounded result. Scope correction: one combined diagnostic command accidentally emitted task2568/result.json and task2568/eval-result.json. Its output exposed a training endpoint-weight summary and aggregate evaluation counters (actual_terminal=512, unknown=0). Those values were not used to derive the task2602 source-map finding; no game-level W/L split, individual evaluation games, or evaluation-query rows were examined. This narrows the original “no weight vector read” statement and preserves the accidental exposure as a scope lapse.
