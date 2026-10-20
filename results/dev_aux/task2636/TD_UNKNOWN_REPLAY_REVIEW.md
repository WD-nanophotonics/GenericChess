# task2636 UNKNOWN training and partial replay review

Question: when a training episode is cut short or ends without a scoring rule terminal, what learner changes remain valid, and what may an independent partial auditor reconstruct?

## Pinned sources

- `results/dev_aux/task2492/learning.py` SHA-256 `88e7f08c0ce2ced7ab7ab9ca53036365bc6c53397db182d173684a194a6c25df`
- `results/dev_aux/task2625/train.py` SHA-256 `12d864caf62f5be604b49a3a6d340defd91c13e43804ecae179a7e56f3c98ea1`
- `results/dev_aux/task2625/audit_training.py` SHA-256 `aa214b2543dbff4cabbf84bda9e68571c15a08e942e3a37af1acfefe49979d82`

## Semantics confirmed

The pinned TDLeaf implementation uses search values as intermediate training targets. Each complete learner search calls `observe`: it performs the TD step from the prior stored prediction/eligibility trace, then stores the current leaf target/prediction for the next step. A completed search with a terminal PV leaf stores a zero-gradient predecessor. An incomplete search calls `reset` and contributes no TD sample; the runner also does not push an action for that receipt. At episode close, only an actual scoring terminal supplies the final ±1/0 outcome to `finish`; `finish(None)` performs no terminal reward update and resets pending traces. Thus an H=128/resource/node/time cutoff or non-scoring terminal is UNKNOWN, not draw, while earlier valid search-target updates in that episode remain part of the model history.

The existing task2625 complete-run auditor reconstructs these learner updates from query rows and the episode's `actual_outcome`, then checks the final weight vector and counters. It requires one episode closure for every query group and every arm at its combined-node cap, so it cannot audit a task2636 partial run as-is.

## Partial-run requirements

- Graceful stop during an active search: retain the incomplete query receipt, apply no action/TD sample for it, close the active episode as UNKNOWN with current node/query counts and model vector, then persist arm/phase/final `STOPPED_USER` status. Do not start another query or episode.
- Graceful stop between searches: close the active episode as UNKNOWN after replaying its complete query prefix; `finish(None)` adds no terminal reward. A stop before a new episode begins creates no episode/query row.
- Evaluation stop before a slot begins leaves that slot missing; a started but unscored slot is completed UNKNOWN only if its closure receipt is durable. Report UNKNOWN and missing separately, with all 512 planned pairs retained in bounds.
- Hard process kill without a final closure remains `NO_FINAL_RECEIPT`; analyze only fully newline-terminated rows, preserve truncated bytes, do not invent closure/model weights, resume, or evaluate.

This confirms the UNKNOWN/terminal reward boundary but does not implement or validate a new runner/auditor. No games, training, or evaluation were started; the frozen plan and sources are unchanged.
