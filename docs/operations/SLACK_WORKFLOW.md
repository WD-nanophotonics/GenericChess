# Slack/dot communication manual

Observed plugin prose rendering may replace leading '- ' with '• '. Root
matching projects the expected prose only; code snapshots/fences, indentation,
body, immutable IDs/hashes and account/channel/thread checks remain exact.
Preserve raw output and the ledger; formatting alone never warrants resend.

The current user accepted active Agent plugin reads/waits, with one native
same-chat heartbeat every90minutes for recovery, updated2026-10-07.
Daily10:00 Asia/Tokyo remains the main consultation window; if no turn is
active, its first continuation after10:00 handles that day once, without
missed-day catchup, another task or concurrent writer.
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
reconciliation, no-loop and no-extra-worker requirements. On2026-10-05 the user
also expressly authorized independent Agent judgment about resend/recontact.
This persists with the same destination scope and stop/revocation conditions.

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
   New inline code snapshots use fenced blocks to retain indentation. A source
   containing triple backticks requires a reviewed attachment. Old request
   messages/hashes are immutable: never regenerate a malformed delivered root.
   If a read strips snapshot indentation, retain the complete raw reply and
   receipt, hold strict import/adoption and continue local research; do not
   normalize code indentation or repost merely to satisfy association.
2. consult --begin-send REQUEST_ID commits SEND_UNCERTAIN before returning
   one Slack plugin send action. Send that exact payload to that channel once.
3. Persist the receipt with slack-bind-sent --request-id REQUEST_ID
   --channel-id C0C6L21UU20 --message-ts 'ROOT_TS'. Always quote the timestamp;
   PowerShell numeric conversion can round away its microseconds. The adapter
   requires all six fractional digits. If send acknowledgement is lost,
   search/read the original channel root and reconcile exact original payload.
   An absent history match alone does not prove nondelivery. Standing authority
   permits a deliberate, evidence-reviewed retry without another user question;
   follow the decision procedure below. Never switch destination/transport.
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
   unpaired markers and changed code still fail exact payload verification. If paginated or an ambiguous rendered delimiter is
   encountered, retain the full tool evidence, reconcile, then assess retry
   need under the standing authorization; do not mechanically repeat a send.
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
   The90-minute continuation reconciles pending IDs after an interrupted turn.
   This explicit active reading cadence replaces the earlier five-minute
   automatic-inbox acceptance gate at the user's request.

New questions use roots. Evidence and decisions stay in their original thread,
TYPE=AGENT_EVIDENCE/AGENT_RESULT. Only explicit new AGENT_REQUEST requests a
review. No self-reply loop, automatic resend or extra delegation. Daily 10:00
Tokyo inspection is the main consultation window for major problems or new
theory. Skip empty/duplicate questions and missed-day catchup. The90-minute local
inspections never require dot discussion/reply. Default to independent project
work between daily inspections; consult only concrete issues worth discussing.
Advice can be read and assessed locally without sending a result/acknowledgement;
follow-ups may wait for the next consultation. Do not spend tokens on routine
back-and-forth or treat silence as a blocker to independent research.

## Deliberate retry/recontact under standing user authorization

Classify the observed situation before acting:

- A connector schema error or automatic review refusal BEFORE execution is
  not an external send. Correct a demonstrated parameter problem and use the
  saved original message; preserve the failed tool result. The pre-send
  SEND_UNCERTAIN marker is a transaction precaution, not evidence of delivery.
- An unknown external result requires exact REQUEST_ID/payload/account/channel
  search and available history reads first. If no root is confirmed, record
  coverage, why delivery remains uncertain, the concrete value of retry and
  duplicate risk. The Agent may decide to retry under the user's authorization;
  absence of a match is not misreported as proof. Persist that decision BEFORE
  the call, use the same ID/message/hash/channel and bind the successful root.
- A known delivered root remains authoritative. A useful reminder or explicit
  request to reconsider belongs in that SAME thread, retaining REQUEST_ID and
  identifying the renewed question. Do not repost a channel root merely because
  dot is silent. If no new useful question/evidence exists, continue research.

Record deliberations and exact receipts in ignored local Slack evidence, with
request ID, original root if known, relevant prior tool/read evidence, reason,
attempt time and outcome. Never clear SEND_UNCERTAIN by assertion, manufacture
a receipt, change immutable request content, lose earlier attempts or create
an automatic retry timer. A failed deliberate attempt requires a fresh review,
not an unbounded loop. Multiple actual roots or conflicting receipts are held
for explicit association; do not adopt responses as though delivery were unique.

The existing begin-send action is deliberately conservative: on dispatched
requests it requests reconciliation and does not mechanically resend. Its
resend_permitted=false denotes NO automatic adapter action; it does not revoke
the user's current authorization for a reviewed native-tool call using the
saved message. No new CLI, daemon, transport or extra worker is introduced.
Automatic approval review can still reject an action; preserve its actual reason
and the direct user authorization rather than claiming the tool has sent it.

## Known send receipt versus payload readback

Observed legacy unfenced-code rendering lost Python indentation. Do not relax
code comparison or resend that known root. `reconcile --snapshot-file RAW
--sent-receipt-file RECEIPT` is an explicit evidence-tier alternative ONLY for
already bound PENDING/COMPLETED roots. Preserve actual successful plugin send
receipt, full paginated read and immutable payload. Match channel/root/link,
original account/thread and unique TYPE/ID/project/committed-base markers.
SEND_UNCERTAIN without a confirmed root still requires exact payload recovery.

The summary exposes request_readback.payload_verified=false and the receipt,
expected/observed hashes. This associates advice, not code bytes or independent
execution. Assess advice against local/public evidence and record that limit
in adopt/defer/reject reasons. No indentation normalization, ledger reset,
automatic resend, new worker or second channel. Later posts still require
explicit review; association does not upgrade old code claims. Receipts and
snapshots are preserved local tool evidence, not cryptographic sender proof.

The receipt-only path also exposes sent_payload_binding_verified=false: a
saved payload hash plus a matching receipt does NOT prove the actual historical
tool-call argument. Keep then-visible parent text/time and reply ts/version;
never reinterpret old advice as review of later edits/code/baselines. Future
sends preserve exact actual arguments/hash together with the returned receipt
as one local call record. Missing historical binding stays missing; never
manufacture it from current text. Receipt-only imports locate a thread, not
payload ownership or independent code review. Shared account still needs
TYPE/project/ID/thread classification, and revisions never auto-reexecute.

## Stop, rollback and isolation

stop persists flags; the calling Agent pauses the native heartbeat and cancels
dot monitoring. Restart never resumes a stop. Rollback preserves ledger, raw
reads, code and Git history; it does not restore older transport/Goal queues.
SQLite ledger is ignored .local_agent/slack/inbox.sqlite3; credentials are
managed by the installed Slack plugin, never extracted into this project.
