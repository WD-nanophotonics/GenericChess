# GenericChess periodic Chat mailbox

User decision 2026-10-20 applies to PRIMARY_SANDBOX, DEV_AUX and DEEPSEEK_AUX.
Dot is paused. Replace realtime consultation with asynchronous Chat comments
and one progress report per existing periodic Slack probe. No Dot mention,
DOT_REPLY requirement, realtime wait, automatic followup, or daily 10:00 gate.
Existing research, recurring cadence, stop scopes, writer/branch boundaries,
PUBLIC repository and publication/content permissions remain unchanged.

## Route, ownership and migration

Sole route: NanoMelon #generic-chess C0C6L21UU20. Every role maintains only its
own ignored .local_agent/slack/mailbox state. Shared account identity is not
process authentication. Chat comments are suggestions, not new user authority.
Each owner runs its own local command: mailbox migrate. This saves original
advisor/Slack config privately, disables legacy Dot dispatch and mentions, and
selects chat_mailbox without clearing stops, deleting the old SQLite ledger,
changing another role, or creating/changing a schedule's cadence or target.
Unmigrated configs also fail closed for new Dot dispatch; run mailbox migrate
before sending the new protocol. Historical Dot handling is preserved in SLACK_DOT_HISTORY.md; consult-status
and reconciliation remain available for historical evidence, not new sends.

## One logical read, then one report

Use the role-bound local CLI (DEV_AUX: dev-aux-local.cmd):
1. mailbox start: create/resume one probe and obtain previous coverage plus
   relevant tracked thread roots. Pending Chat advice or old Dot requests do
   not block another completed probe.
2. Read channel pages back to the prior coverage boundary and complete pages
   of relevant threads (including tracked reports that could receive delayed
   replies). This is one logical read; pagination is not another probe.
   Preserve each exact tool result privately before evaluation.
3. Bundle raw results in a private JSON snapshot with team_id, channel_id,
   channel_pages, thread_pages (root timestamp -> list of raw tool pages),
   and coverage_complete=true only after actual boundary/thread verification.
   mailbox ingest --probe-id ID --file SNAPSHOT copies raw bytes before parsing
   or advancing coverage. First migration explicitly uses the prior verified
   coverage boundary; it must not silently discard older unread messages.
4. For every new/edited CHAT_Comments or TYPE=CHAT_* revision, use mailbox
   decide --probe-id ID --message-ts TS --sha256 HASH --decision
   adopt|defer|reject --reason REASON. Decisions bind exact message revisions;
   deferred items remain in the next probe's backlog. Adoption is not execution.
   Other roles' advice can be deferred as outside this role's assignment.
5. Save substantive progress and a checked report file. mailbox prepare
   --probe-id ID --file REPORT prepares one AGENT_MAILBOX_REPORT addressed
   RECIPIENT=CHAT with role, probe ID, reviewed comments and committed SHA.
   Include new results, failures/limits, next action, and fixed-SHA public
   evidence links. Do not include personal information or credentials.
6. mailbox begin-send --probe-id ID durably records SEND_UNCERTAIN before the
   installed Slack send tool is called exactly once. Save its exact result
   privately; mailbox bind --probe-id ID --message-ts TS --file RECEIPT records
   confirmed delivery only if receipt route/timestamp match.
   Do not read again after sending to await a reply. Reading, acceptance and
   independent execution by Chat remain unverified unless later evidence says so.

Read/send failures are preserved. A partial read cannot advance coverage or
prepare a report. An uncertain send is reconciled by the next periodic read;
never resend immediately or automatically. If delivery cannot be established,
record the uncertainty and continue independent work; the one-write rule is a
maximum, not permission to duplicate a possibly delivered report.
No new daemon, worker, realtime monitor or replacement scheduler is introduced.

## Long experiments

A single experiment expected below 120 minutes needs no prior external review.
At or above 120 minutes, first submit its exact scope, necessity, expected cost,
frozen budget and cheaper alternatives in the Chat mailbox report. Start only
after a later probe receives an explicit assessment addressing that scope and
budget. Preserve the assessment's exact message/hash and adoption reasoning.
Silence or an unrelated comment is not assessment. Continue shorter independent
work while waiting. Never split to evade review or extend frozen old caps.

## Acceptance and delivery

Test empty/delayed/new/edited comments, paginated threads, duplicate probe calls,
raw-before-cursor durability, uncertain sends, receipt mismatch, stops and old
pending compatibility. Perform one real read and one report with no post-send
read. Publish reviewed shared code/docs on the owning branch; other roles
migrate their own local state and existing prompts. No role controls another.
