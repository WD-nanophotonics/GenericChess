# DEV_AUX2623 — corrected SAME fixed-scale Generic training attempt

## Registration

Task2623 is a separate registration following task2622's pre-query plan/runner
schema failure. It uses the same unchanged task2622 v2 outcome-blind root pool,
but corrected consumer paths and fail-closed preflight checks. The frozen plan
binds 29 source hashes, 16 exact rule/seed initialization vectors, 16 arms at
250,000 candidate-plus-foe nodes each, and 1,024 evaluation slots. Its expected
combined cost was 66.70 minutes, below the 120-minute mailbox-assessment line.
Plan SHA: `a9898ce0…4118c52`; registration SHA:
`d985943a…e4ce7dfa`.

The prior task2622 failure remains intact. It had zero queries and episodes and
is not counted as training or evaluation. Task2623 began once under its own
directory and registration.

## Partial training and interruption

After about ten minutes, live file-size snapshots showed zero while the writer
was open. I treated that as no progress and interrupted the original command
session. Once the process closed, the persisted streams contained 26,176 query
rows (112,153,431 bytes) and 1,862 closed episode rows (5,057,729 bytes), all
valid JSON lines. The initial interruption receipt's zero-row counts were
wrong; its post-interruption file hashes are correct. The correction and
complete hash/size inventory are in `run/training-interruption-correction.json`.
This was an avoidable monitoring mistake. No retry or top-up followed.

Independent replay in `run/partial-training-audit.json` reconstructed all
26,176 search records, full GameSession histories, legal actions, fixed-scale
weights, and TDLeaf updates. It accounts for 1,470,789 total nodes: 828,758
candidate nodes and 642,031 foe nodes. Five arms reached 250,000 nodes; arm
271002/8173 reached 220,789. Those six arms closed 1,862 episodes with 1,845
actual terminals and 17 UNKNOWN outcomes; 1,211 closed episodes changed a
weight. The last arm also has one open 13-query/1,594-node episode with no
closure or terminal label. Ten registered arms were never started.

These terminal labels and updates are partial training evidence, not a strength
comparison. No `training-result.json` exists, so no evaluation binding or
evaluation was allowed. All stop, node, and scope limits remain in force.

## Exposure and limits

All 120 registered training root families were observed for rules 271001 and
271002; no training episodes began for 271003 or 271004. An exact full-record
check of 21,918 distinct logged training histories against all 64 evaluation
roots found zero intersections. The evaluation roots remain unstarted. This
comparison excludes unlogged interior search states and semantic/transposition
equivalence. Any future fresh training design must account for the exposed
271001/271002 training histories and preserve this partial run as-is.

Twenty-six targeted tests passed before launch. The partial replay audit passed
after interruption. The result is **incomplete**: no learner-strength estimate,
paired evaluation, or generic-transfer conclusion is available.

The interrupted `queries.jsonl` and `episodes.jsonl` originals remain local.
`run/public-partial-traces.json` records deterministic gzip copies with
byte-exact decompression checks and source/archive SHA256 values; these compact
copies preserve the partial evidence for remote review without changing or
completing the failed run.
