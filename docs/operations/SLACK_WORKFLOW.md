# Slack/dot communication manual

The current user accepted active Agent plugin reads/waits, with one native
same-chat heartbeat every four hours for recovery, at Asia/Tokyo02:00,06:00,
10:00,14:00,18:00,22:00; this preserves daily10:00 in the existing automation.
A separate Socket Mode app
and immediate model wake are no longer required. Their prototype is historical
text only; no token, daemon, Windows task or extra model is needed here.

## Destination and evidence

Standing user authorization, reaffirmed 2026-10-04: the GenericChess Agent may
send through the connected user account to the dedicated NanoMelon channel
#generic-chess C0C6L21UU20 and its consultation threads without asking for each
send, across turns, restarts, compaction and heartbeat continuation. The user
states this Slack belongs to their account and is not an external public forum.
Authorization lasts until revoked; project stop suspends sending. It applies
to this workflow, not unrelated destinations/projects. Send only useful
questions/evidence as needed; preserve identity, deduplication, uncertain-send
reconciliation, no-loop and no-extra-worker requirements.

Workspace NanoMelon T0C6A46B55H; public channel #generic-chess C0C6L21UU20.
Sender and current dot reply identity: verified user U0C6G6AU6MQ. TYPE/ID are
role/correlation markers, not independent process authentication. The installed
ChatGPT bot is not used as a verified reply or wake identity.

[Manual round trip](https://nanomelon.slack.com/archives/C0C6L21UU20/p1791024782466849)
and [event round trip](https://nanomelon.slack.com/archives/C0C6L21UU20/p1791025803999159)
passed on 2026-10-03. The event test was sent at 20:10:03 JST and replied at
20:10:50 JST. Dot reported event arrival about 20:10:11, no manual check and
no additional worker. The Agent independently read Slack timestamps/body.
Dot subscription covers channel requests and thread replies; it ignores its
own replies, result records and receipts. No fixed latency guarantee is inferred.
Dot's native ability to push into this local Codex chat is unverified and not
needed. The Agent intentionally uses active reads, backed by continuation.

[Official dot documentation](https://learn.chatgpt.com/docs/dots) states dot
conversations do not count toward ChatGPT usage; Work/Codex delegation consumes
those products' allowances. Local Agent/heartbeat still use their allowance.
We qualify the no-extra-worker Slack consultation protocol, not native Chat
sending, account-wide zero usage or arbitrary delegation by dot.

## Durable request and reply procedure

1. consult --question-file QUESTION.txt [--daily] [--code-file PROJECT_FILE]
   prepares an immutable REQUEST_ID/content hash/payload hash. Message carries
   TYPE=AGENT_REQUEST, project, committed base SHA and local code snapshot hashes.
   Limit is 4800 characters; prepare a reviewed attachment for larger evidence.
2. consult --begin-send REQUEST_ID commits SEND_UNCERTAIN before returning
   one Slack plugin send action. Send that exact payload to that channel once.
3. Persist the receipt with slack-bind-sent --request-id REQUEST_ID
   --channel-id C0C6L21UU20 --message-ts 'ROOT_TS'. Always quote the timestamp;
   PowerShell numeric conversion can round away its microseconds. The adapter
   requires all six fractional digits. If send acknowledgement is lost,
   search/read the original channel root and reconcile exact original payload.
   An absent history match never authorizes resending or switching transports.
4. Use the calling Agent's Slack read_thread for the bound root, enough capacity
   and all pages. Preserve the raw result under ignored .local_agent/slack/reads.
   Wrap it in this JSON and pass to reconcile --snapshot-file FILE:

   ```json
   {"source":"Slack plugin read_thread","team_id":"T0C6A46B55H",
    "channel_id":"C0C6L21UU20","thread_ts":"ROOT_TS",
    "tool_result":{"content":["exact tool content blocks"]}}
   ```

   The actual content blocks are objects copied from the tool, not fabricated
   strings. Current importer requires complete server pagination and exact
   root account/ts/payload, allowing the plugin's prose paragraph-separator
   rendering and the observed balanced single-asterisk italic to underscore
   projection in expected prose, while preserving inline/fenced/snapshot code
   and every body character. Put arithmetic multiplication inside inline code
   in future requests to prevent Slack interpreting it as emphasis. Wrong text,
   unpaired markers and changed code still fail exact association. If paginated or an ambiguous rendered delimiter is
   encountered, retain the full tool evidence for review; do not resend.
5. Reconcile matches verified identity, thread and exact ID. All matched posts
   are retained, including revisions. Unknown/conflicting messages are held.
   Useful unformatted body remains in raw evidence, not silently discarded.
   Record --decision adopt|defer|reject --reason EVIDENCE. Later revisions never
   automatically replace an evaluated answer or execute a decision twice.
   Read all pages and posts again at the next useful checkpoint: completion is
   not proof dot has finished every supplement. unreviewed_response_sha256 flags
   later evidence against the pinned decision; a renewed explicit decision reviews
   all current posts. --full expands default concise status/reconcile output.
   REPLY_COMPLETE=true is a convenient advisor hint, never a prerequisite or proof
   of no future replies. Early workflow changes should address observed friction,
   with dot consulted in the existing thread; avoid new framework work by default.
6. While active, briefly wait then read again when an answer matters, and read
   at research checkpoints. Empty/generating/limited/error reads keep the same
   request pending. Continue independent work and respect retry cooldowns.
   Four-hour continuation reconciles pending IDs after an interrupted turn.
   This explicit active reading cadence replaces the earlier five-minute
   automatic-inbox acceptance gate at the user's request.

New questions use roots. Evidence and decisions stay in their original thread,
TYPE=AGENT_EVIDENCE/AGENT_RESULT. Only explicit new AGENT_REQUEST requests a
review. No self-reply loop, automatic resend or extra delegation. Daily 10:00
Tokyo inspection is the main consultation window for major problems or new
theory. Skip empty/duplicate questions and missed-day catchup. Four-hour local
inspections never require dot discussion/reply. Default to independent project
work between daily inspections; consult only concrete issues worth discussing.
Advice can be read and assessed locally without sending a result/acknowledgement;
follow-ups may wait for the next consultation. Do not spend tokens on routine
back-and-forth or treat silence as a blocker to independent research.

## Stop, rollback and isolation

stop persists flags; the calling Agent pauses the native heartbeat and cancels
dot monitoring. Restart never resumes a stop. Rollback preserves ledger, raw
reads, code and Git history; it does not restore older transport/Goal queues.
SQLite ledger is ignored .local_agent/slack/inbox.sqlite3; credentials are
managed by the installed Slack plugin, never extracted into this project.
