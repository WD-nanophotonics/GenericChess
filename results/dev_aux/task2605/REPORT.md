# Task 2605 — direct recurrence audit of outcome-gated TD(lambda)

## Question and scope

Does the task2593 episode learner implement its written per-residual eligibility formula, and do the frozen baseline endpoints use the same episode-update schedule? This is a source-and-algebra audit only. It does not register, train, tune, or evaluate a new arm.

## Evidence

- `task2593/design.json` is still marked `PROPOSAL_NOT_REGISTERED_OR_STARTED`.
- `task2593/episode.py` implements each residual's eligibility as a direct finite sum. A terminal target selects lambda 1 for that residual; other search targets and final known W/L use the base lambda. Unknown final outcomes stop before the final residual; incomplete receipts are not appended.
- `task2568/train.py` imports and instantiates `TDLeafEpisode` for the ordinary TD arm, calls `observe` on each complete candidate-side search, and `finish` once after each game. Thus the frozen task2568 baseline endpoints share episode-frozen updates; task2492/run.py's separate online `TDLeaf` smoke path is not the task2593 baseline. The apparent update-timing confound is rejected.
- The later task2594 registration and report resolve the old task2593 exposure issue with a separately registered comparison. Its baseline counts were 37/66/38/45 terminal-target residuals by seed; its candidate reached 54/64/55/43. The registered aggregate gate passed and the report found a finite-panel strength gain. This is prior evidence, not a new result from this audit.

## Independent verification

Added `test_exact_reference.py`, which calculates the documented residual-by-residual matrix from the literal finite-sum equation, separately from the candidate implementation. It also checks lambda=1 equivalence with the frozen `TDLeafEpisode` and rejection of mid-episode weight mutation.

Command: `.venv/Scripts/python.exe -m unittest results.dev_aux.task2593.test_episode results.dev_aux.task2605.test_exact_reference -v`

Result: 7 tests passed (4 existing candidate tests, 3 independent reference/invariant tests). No chess games were run. Training and Generic transfer claims remain exactly as reported in task2594 and the current route.

## Decision and next action

The equation and baseline wiring are consistent, so no source correction is justified. Retain task2593 as its historical unregistered proposal; use task2594's registered finite-Chess outcome as the basis for the next step. Next: prepare a bounded, pre-registered Generic-rule transfer with the same episode learner, full Generic rule/history semantics, frozen opponent and paid-cost accounting, and actual W/L/D validation. Do not infer universal price order or alter product defaults/UI.

## Environment evidence

The normal sandbox subprocess cannot chdir into this DEV_AUX checkout because it is not among the active runtime's writable roots; own-checkout Git and reversible write/read/delete probe succeed through the supported escalated execution path. Git remote connectivity is healthy. No ACL, security, app, or other-role state was changed.