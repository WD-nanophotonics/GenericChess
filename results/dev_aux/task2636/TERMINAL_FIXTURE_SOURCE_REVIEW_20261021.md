# task2636 actual-terminal fixture source review

## Question

Can the required real-scoring-terminal replay test be built from already saved
task2636-candidate histories, without starting another search/evaluation sample?

## Evidence and method

The frozen `candidate-history-inventory.json` is an outcome-blind scan over the
then-existing 10,110 plain JSON/JSONL and 27 compressed result files under
`results/dev_aux` (10,137 files scanned). For each of the 16 task2633 candidates it records four exact
full-history matches, all from
`results/dev_aux/task2635/run-v2/episodes.jsonl` (file SHA-256
`6ed7bee558d1077de78905d98aa3133bf6b43bccb59150cb11e96a602c032254`). The
inventory pins candidate fingerprints and exact canonical record hashes; it
does not authorize replaying outcomes as learner results.

Read-only inspection of that pinned source found 64 rows: 57 ended
`PLY_CAP_UNKNOWN`, seven ended `NO_BOARD_ACTION_UNKNOWN`; all 64 report
`outcome_read=false` and `full_history_replay=true`. No row is an
`ACTUAL_TERMINAL` record. These saved histories can support full-history and
UNKNOWN replay fixtures, but they do not exercise the actual W/L/D closure path.

## Decision and limit

The existing source inventory does not supply the required actual-terminal
fixture. Do not synthesize a claim of terminal coverage from a horizon or
no-board-action UNKNOWN, and do not create a new evaluation sample to fill the
gap. Keep task2636 unregistered. A later actual-terminal test needs a preserved,
legal source record under a byte-pinned candidate rule; if none is found in the
authorized saved corpus, the terminal-audit gate remains open and the all-in
registration decision cannot pass on current evidence.

This is a source-availability audit only. It does not establish full-corpus
absence outside the inventory's `results/dev_aux` scope, actual candidate
strength, terminal-frequency, or any changed estimate of runtime. Frozen
roots, rules, caps, source pins, and run state were not modified; no training,
search, evaluation, or outcome read was performed.

Next, continue the read-only integration/cost review of receipt binding and
stop-safe writes, keeping the existing 6,600-second design cap and no-run
status.
