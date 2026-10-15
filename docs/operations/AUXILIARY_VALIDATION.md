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
Ordinary concurrent projects are allowed. Keep file and computation-state isolation;
relevant load conditions limit timing interpretation without requiring quiet windows.

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


## Current user publication grant2026-10-15

This supersedes older origin-based publication exclusions in this checkout's
manuals. The user authorizes ANY GenericChess-related project content on the
established delivery branch origin/sidemission and dedicated project Slack,
provided the ACTUAL outgoing contents contain no personal information, passwords
or credentials. Source/data/configuration, failed/partial results, diagnostics,
checked project-only records and sanitized evidence are covered regardless of
origin. Preserve exact sensitive originals in Git-ignored .local_agent; inspect
and sanitize publication copies as needed. Fixed authorized routing IDs remain
permitted. Continuing authorization survives restart/compaction; no per-upload
approval queue. Supported tools/escalation only; report actual persistent denial.
Separate checkouts/branches, stops and machine safety remain mandatory.
