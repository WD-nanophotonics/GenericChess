# GenericChess Slack workflow

Status on 2026-10-03: implementation staged, automatic dispatch disabled.
The existing Slack plugin read/write and one manually triggered dot round trip
passed. Socket Mode live receipt, latency, reconnection and dot subscription
have not passed. The paused heartbeat stays paused. Courier and native Chat
sending stay disabled; historical records remain evidence.

## Verified destination and roles

- Workspace: NanoMelon, `T0C6A46B55H`.
- Public channel: `#generic-chess`, `C0C6L21UU20`.
- Plugin-authenticated sender: W D, `U0C6G6AU6MQ`.
- Actual dot reply on the test thread also used `U0C6G6AU6MQ`.
- Channel ChatGPT bot `U0C6L1MJS0L` is not a verified automatic route to dot.
- Test: `GC-SLACK-20261003-01`, root `1791024782.466849`.
  [Test thread](https://nanomelon.slack.com/archives/C0C6L21UU20/p1791024782466849).

The root was posted at 19:53:02 JST; dot replied at 19:58:00 JST after
the user asked it to inspect the channel. That measures approximately 298
seconds of manual-trigger/reply delay, not receiver latency. No mechanical
receiver was running. Full plugin evidence is in Git-ignored
`.local_agent/rebuild/slack-probe-01-thread.json`.

Shared user identity proves the Slack account only. TYPE and REQUEST_ID route
messages, not authenticate the producing process. Unknown actors, mismatched
IDs and threads are held. If independent dot bot identity is later verified,
configure user/bot/app metadata explicitly; do not silently change bindings.
Missing formatting does not destroy useful text: every target-channel event
is persisted, but incomplete replies need explicit review before adoption.

## Create the separate receive-only app

This app receives local evidence; it does not wake dot, send messages or call
models. Dot's new-message monitor is configured independently on the dot side.

1. Open [Slack app management](https://api.slack.com/apps), choose Create New
   App / From a manifest, and select **NanoMelon**. Import
   `docs/operations/slack-receiver-manifest.json`. Verify the sole bot OAuth
   scope is `channels:history`, with `message.channels` event subscription.
   Do not grant `chat:write`, DM/private-channel history or unrelated scopes.
2. Install the app in NanoMelon. In Slack, add **GenericChess Inbox** only to
   `#generic-chess`. Channel-history access follows app membership; the scope
   itself is not a channel allowlist. The receiver also enforces team/channel
   IDs and rejects all other targets. Keep membership limited to this channel.
3. Enable Socket Mode (the manifest enables it). Under Basic Information,
   generate an app-level token with `connections:write`. This scope opens a
   websocket; it does not authorize posting messages. Obtain the bot OAuth
   token from OAuth & Permissions.
4. In a local terminal in this checkout, run:

   ```powershell
   .venv\Scripts\python.exe -m tools.local_agent.cli slack-credentials
   ```

   Enter app and bot tokens at hidden prompts. Do not paste tokens in this
   chat, files, command arguments, Git or logs. They are stored directly using
   keyring's Windows Credential Manager backend under
   `GenericChess-Slack-T0C6A46B55H`.
5. After installation/membership is confirmed, set only
   `.local_agent/slack.json` `receiver_enabled=true`; preserve `stopped`.
   If explicitly stopped, user authorization to resume is required before
   clearing that flag. Run `slack-receive` in a dedicated local terminal.
   Single-instance lock prevents a second receiver. No Windows scheduler or
   separate model execution is created. Credential/auth errors remain fatal;
   the SDK manages websocket reconnects without resending consultations.

The preflight verifies the bot's workspace and exact `channels:history` scope.
If Slack does not expose the scopes in the auth response, it fails closed;
inspect the app configuration rather than weakening the scope gate silently.
Socket Mode requires no public HTTP endpoint.
[Slack documentation](https://docs.slack.dev/apis/events-api/using-socket-mode/).

## Calling Agent interface after acceptance

Set `.local_agent/advisor.json` transport to `slack` only after acceptance;
retain the earlier configuration as recovery evidence. The `consult`,
`consult-status` and `reconcile` entry points then select this adapter.

```powershell
.venv\Scripts\python.exe -m tools.local_agent.cli consult --question-file QUESTION.txt
.venv\Scripts\python.exe -m tools.local_agent.cli consult --begin-send REQUEST_ID
```

`begin-send` commits SEND_UNCERTAIN before returning the immutable message
and destination for the calling Agent's `Slack` plugin. Invoke that plugin
once, then persist its successful receipt:

```powershell
.venv\Scripts\python.exe -m tools.local_agent.cli slack-bind-sent --request-id REQUEST_ID --channel-id C0C6L21UU20 --message-ts ROOT_TS
.venv\Scripts\python.exe -m tools.local_agent.cli reconcile --request-id REQUEST_ID
.venv\Scripts\python.exe -m tools.local_agent.cli slack-wait --request-id REQUEST_ID --seconds 300
```

Wait is mechanical only; shell calls must yield in under 60 seconds while it
runs. No file change is claimed to wake an idle Agent. Read inbox on activity
checkpoints and before continuing a restored chat. A message after uncertain
send is reconciled against its exact original payload/account/channel; never
send again because the receipt was lost. If event history missed that root,
use plugin thread reads and retain the evidence for explicit binding review.
No automatic history search or resend is performed by the read-only app.

The inbox is SQLite WAL under Git-ignored `.local_agent/slack`. Event IDs
deduplicate retries. Text, sender metadata, original payload, thread, edits
and receive timestamps are durable. Reconciliation timestamps Agent reads;
reply revisions are retained without replacing an adopted conclusion.
TYPE=AGENT_RESULT and ordinary receipts do not create consultations.

Messages include a unique ID, project and committed base SHA. Local code
snapshots have content hashes and are not claimed to equal the base commit.
The single message is bounded to 4800 characters; larger evidence requires a
reviewed attachment. Sending errors (login, rate limit or disconnection) leave
the original request uncertain and never permit an automatic retry.

Dot must confirm a channel-scoped monitor of explicit AGENT_REQUEST, including
thread replies, ignoring its own replies/results/receipts. Only explicit new
review requests trigger it. No automatic Work/Codex delegation is permitted.
[Official dot documentation](https://learn.chatgpt.com/docs/dots) says dot
conversations do not count toward ChatGPT usage, while delegated Work/Codex
tasks consume their respective allowances. This is not a claim that local
Agent execution is free or that account counters isolate consultation usage.

## Remaining acceptance and stop

- Receive a real dot reply through the live Socket Mode app and match exact
  account, thread and request ID. Verify reply-post→persist and post→active
  Agent-read are each within 300 seconds. Dot generation time is separate.
- Validate real disconnect/reconnect, auth expiry and rate limit behavior;
  synthetic tests alone do not qualify these live paths.
- Confirm dot's actual event subscription and a fresh request triggers it.
- Verify same-chat heartbeat continuation and no overlap before activation.
- Keep only this Slack consultation channel active after acceptance, and
  update the existing paused heartbeat rather than creating another one.

`slack-stop` persists stopped=true, disables dispatch/receiver and makes the
running receiver exit. The calling Agent must also pause the existing native
heartbeat and tell dot to cancel this channel's monitoring. It must not
claim those remote actions were done merely because the local stop succeeded.
Restart never clears stop state.

Rollback: stop receiver, keep dispatch disabled and preserve inbox/config/probe
evidence. Do not automatically revive Courier, native Chat, old schedules or
queues. Git and scientific work artifacts are unaffected.
