# Task 2618 training interruption (2026-10-20)

The write-once `learner-comparison-v1` registration was valid at launch
(`plan_sha256=d599e008ee76d2d940899bcd2b6b22bc8afeb2ac02d5044400f6eb8c42604f2e`;
session `41743655-0274-443c-a3c8-d5fa7526b3a6`). The run did not complete.
It started only TreeStrap seed index 0, reached its 1,000,000 combined
candidate-plus-foe node cap after 51 started root slots, and left the remaining
11 arms unstarted. Among those 51 episodes, 47 ended at actual terminals, three
were horizon-unknown, and one was search-resource-unknown. The partial output
has 120 planned rows, 69 explicitly marked unstarted, and 10,096 search-query
rows. It contains no evaluation and supports no learner comparison or strength
claim. Exact original JSONL files remain untouched in the local worktree.

`training-result.json`, a process exit code, and captured stdout/stderr were
not produced or retained. A narrow Windows Application query found no 1000/1001
crash event in 2026-10-20 05:13–05:20 UTC; this does not identify the exit
cause. The prior command session handle was not retained, so interruption
provenance is unknown. The source path shows a likely diagnostic gap around the
first-arm completion report, but neither a broken output pipe nor host/session
termination is established as the cause. Do not infer an environment failure,
replay the registered plan, top it up, or convert the partial outcomes into a
complete run.

To prevent loss of the last completed-arm summary, the runner now appends and
`fsync`s `arm-progress.jsonl` immediately after each arm, before continuing. It
no longer writes one progress line to the console per arm; the final result is
persisted as the run artifact. Registration preflight treats the progress file
as a write-once output and refuses reuse. A regression test simulates failure on
the next arm and confirms the first completed arm remains durable while no
misleading final result is emitted. Focused task2618 tests: 15 passed;
`compileall` and `git diff --check` passed.

Next: preserve v1 unchanged, build a separately registered v2 with a new
outcome-blind set of unexposed training roots, and retain the same 1M-per-arm,
3,600-second evaluation, and 6,600-second all-in caps. Launch only through a
tracked execution session that retains its session handle and final exit
receipt. Recompute the estimate from the revised inputs; if it reaches 120
minutes, first request an exact-scope Chat mailbox assessment. Evaluation stays
ineligible until every training arm has completed its registered node dose.
