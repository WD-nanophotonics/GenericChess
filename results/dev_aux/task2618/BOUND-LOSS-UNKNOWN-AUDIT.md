# Task2618 bound-loss and UNKNOWN audit

Date: 2026-10-20. Scope: read-only contract audit of the already-registered v4 trainer; no registered code, roots, caps, outcomes or weights were changed or selected.

## Finding

The frozen training path preserves search bounds and censors unknown game outcomes as intended. `TreeStrap.update` accepts only complete receipts, maps each minimax sample interval through the configured `tanh` transform, and uses `interval_error`: zero gradient contribution while the prediction lies inside the interval, otherwise the nearest violated boundary. It computes the batch against the pre-update parameter snapshot and applies one mean semi-gradient afterward. AlphaBeta marks fail-high/fail-low as one-sided bounds; a resource-aborted search returns an incomplete receipt with no samples, so it cannot be promoted into an exact target.

For TDLeaf, the trainer observes only complete candidate searches. At episode end, `finish(..., outcome=None)` stops before adding a fabricated terminal target, but keeps valid adjacent residuals between prior completed search observations. Thus UNKNOWN censors the terminal residual; it does not discard all earlier within-episode learning, and it is never converted to a draw. The WDL control uses actual terminal outcomes only; an unknown reward is [-1,+1], and the paired four-slot proposal is accepted only when its complete interval is strictly positive.

No defect found in these paths. This is a source/test contract finding, not evidence of convergence or strength. Root-window bounds are training constraints, not exact values; terminal game outcomes are separate from search receipts.

## Evidence

The three audited implementation files match the v4 immutable registration pins:

- `results/dev_aux/task2618/train_learners.py`: `18be47f61c9869ea1d20e2521031fa541e88523c19171313f24b01911a4944ae`
- `results/dev_aux/task2492/learning.py`: `88e7f08c0ce2ced7ab7ab9ca53036365bc6c53397db182d173684a194a6c25df`
- `results/dev_aux/task2492/episode.py`: `c1798654adbad62dbd8ddbcba836ac05469b0c7f99ee7db1b9f9f34303daa0e0`

Relevant code: `task2618/train_learners.py` complete-receipt gating and `SEARCH_RESOURCE_UNKNOWN` handling (around lines 257-310); `task2492/learning.py` `interval_error` and `TreeStrap.update` (lines 103-107, 241-259), AlphaBeta incomplete return (219-223); `task2492/episode.py` censoring (17-25); `task2618/wdl_receipt_adapter.py` reward bounds and paired acceptance (32-69).

Focused regressions passed: 28 tests across `task2492/test_learning.py`, `task2492/test_episode.py`, `task2618/test_train_learners.py`, and `task2618/test_wdl_receipt_adapter.py`. The first invocation from the wrong current directory failed collection because the package root was not on `sys.path`; rerunning from the DEV_AUX checkout passed all 28, with no source edits.

At the 07:14Z checkpoint, the single registered v4 training process (PID 27532) remains active. Its append-only progress file contains 10 arm summaries, all at their registered node budgets, including 2 with a censored block; cumulative totals are 10,000,000 paid nodes, 574 actual terminal games, 12 UNKNOWN games and 1,694 unstarted/missing slots. These are progress counters only; all 12 registered arms have not finished, no evaluation has started, and no outcome/strength conclusion is claimed. The process must continue under its existing caps; no relaunch, top-up or cap extension.

## Next action

Preserve the active run and wait for its existing bounded launcher to exit without starting another writer. Validate the exit receipt and all 12 arm summaries against the frozen registration. Open the separate registered evaluation only if training fully qualifies; otherwise preserve failure/partial data and stop there. Report only the checkpointed status and fixed published SHA.