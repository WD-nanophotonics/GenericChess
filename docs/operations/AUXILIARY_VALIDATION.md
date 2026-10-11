# Auxiliary validation handoff

User2026-10-11 established these simple participant names:

|Participant|AGENT_ID|Branch|Work|
|---|---|---|---|
|Primary Agent|PRIMARY_SANDBOX|sandbox|Mainline research, product changes and final integration/publication|
|开发辅助|DEV_AUX|sidemission|Independent validation, bounded counterexamples and its own evidence|
|Dot|DOT|No local writing|Research advice and review of actual evidence|

The user confirmed that 开发辅助 belongs to this same GenericChess project and
shares the Slack account. These fixed IDs are ordinary routing labels under
that user-confirmed assignment. No per-message identity challenge, secret token,
extra registry approval or complex authentication flow is required. Shared Slack
account identity does not cryptographically prove which Agent wrote a message;
we state that limit rather than block routine collaboration.

## Writing boundary

Each Agent uses a separate checkout/worktree on its branch. Never switch the
branch in the other's checkout or write its session/memo/stop/cache/evidence.
The primary remains the sole sandbox writer. 开发辅助 must not run the primary's
session, consultation-ledger or sandbox publication commands against shared
.local_agent state. It owns its local state and only its assignment outputs.
A separate Git branch in the same working directory is insufficient isolation.
UI Test stays isolated. Do not touch alphasho or other projects.
Concurrent projects and independent Agent computations are normal and allowed.
Do not reserve source-only timing windows or request another Agent to pause.
Respect separate files and running computation/state; describe relevant timing
noise briefly without treating ordinary concurrent load as a boundary violation.

The user is establishing 开发辅助; the primary does not automatically spawn
workers. Once its chat exists, a direct message can carry the handoff. Until
then this file and the assignment file are ready for it to read. A missing
chat ID does not prevent preparation or ordinary file communication.

## Simple exchange

A task file contains a short task ID, fixed base SHA, question, command/inputs,
expected evidence and completion condition. The validator writes a result with
that same task ID, actual command/backend/limits, output files, successes,
failures and limitations. Source/artifact hashes ensure reproducibility; they
are evidence checks, not a communication admission process. Primary reviews
adopt/defer/reject and integrates deliberately. Never edit an old result to agree.

Same-machine fallback uses separate producer directories in an agreed shared
handoff location: primary writes tasks, DEV_AUX writes results. Write files
atomically on completion and do not overwrite the other's files. For another
machine, use sidemission or agreed file transfer; a local path grants no remote
access. Publish Agent-produced evidence only; exclude user/private inputs,
raw Slack/account records and credentials.

## Slack

Use only NanoMelon #generic-chess. Put PROJECT=GenericChess, AGENT_ID and
RECIPIENT in the message. Use the existing REQUEST_ID for a consultation or a
short TASK_ID for an assignment/result. Dot replies to the requesting AGENT_ID.
User-directed new Dot questions always create a new root with TYPE=AGENT_REQUEST
and a fresh REQUEST_ID, never AGENT_FOLLOWUP. Evidence/results use the related
thread and do not require Dot to reply. Messages to the primary use
RECIPIENT=PRIMARY_SANDBOX; auxiliary requests use RECIPIENT=DOT.

Do not infer guaranteed wake/receipt/reply from a label. Read new roots and
relevant threads at useful checkpoints, all pages, and continue independent
work. No self-reply loops or automatic resend. Do not wait for Dot to approve
ordinary validation. Existing raw-body persistence restrictions are reported
separately; do not fabricate strict imports or turn them into a research gate.

## Validation constraints

Keep frozen source/data/conditions and actual backend/fallback/evaluator visible.
Cross-machine timing is descriptive, not a controlled speedup claim. Small
interruptible runs are allowed; a single run expected above one hour first
gets Dot's necessity assessment. Stop flags, human-data boundaries, machine
safety and no uncontrolled jobs remain. A result does not automatically merge
code or change q/evaluator/UI defaults.


## Published collaboration summaries — user2026-10-11

Primary keeps docs/operations/COLLABORATION_LOG.md as concise segment summaries
of both participants' contributions, actual coordination, disagreements/errors,
adopt/defer/reject decisions, efficiency evidence and unresolved issues. Update
at completed segments and publish with reviewed Agent-only work to sandbox;
verify the full remote SHA and provide Dot a fixed-revision link for review.
Preserve corrections and references; exclude raw messages/account/private data.
No invented speedup or guaranteed receipt/reply/review. No auxiliary activity
is recorded honestly; summaries do not require waking the auxiliary for routine
acknowledgements or adding approval/identity gates. Scientific evidence remains
in each participant's existing purpose-specific outputs.

## Concurrent local work — user2026-10-11

Multiple projects and Agents running on this computer are normal. Do not ask
other projects or DEV_AUX to pause, obtain source-only timing windows, or treat
ordinary concurrent computation as a collaboration violation. The boundary is
unauthorized writes to another Agent's files or direct alteration of its running
computation/state. Keep separate checkouts and sole sandbox publication.
For timing evidence, report observed concurrent load briefly when relevant;
use paired/counterbalanced comparisons and actual work/backend counters. Do not
claim machine exclusivity or noise-free speedups. Ordinary load variation is an
interpretation limit, not a stop/approval gate, a reason for automatic reruns or
extra process monitoring. Preserve frozen raw results and earlier declarations;
this user instruction supersedes the earlier resource-window practice without
retrospectively converting old timing evidence into a clean benchmark.
