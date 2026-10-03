# Local Agent operations

The user selected Slack/dot as the replacement consultation workflow.
See [Slack setup and acceptance](SLACK_WORKFLOW.md). Channel read/write and
manual and event-triggered dot round trips passed; the receive-only app is
pending. Both older transports remain disabled. The single native
heartbeat has been updated for Slack and remains PAUSED until live acceptance.
The native/Courier procedures below are historical recovery capability notes,
not authorization to switch back or send while the Slack cutover is pending.

The primary checkout is `GenericChess 2`, on `sandbox`. The current App's fresh
configuration is the baseline. Read `AGENTS.md`, the research mainline, and
`.local_agent/NEXT_WORK.md`; old exported tasks and queues are evidence only.

## Native advisory exchange

The calling Agent uses its existing app tools; no script creates a model worker
or connects to an undocumented app endpoint. Advisor identity lives in the
Git-ignored `.local_agent/advisor.json` and was verified against old receipts.

1. Prepare: `generic-chess-local.cmd consult --question-file <file>`.
   Add `--daily` for the 10:00 Tokyo consultation and `--code-file <file>` for
   bounded UTF-8 project code. No prior Git publication is required.
2. `consult --begin-send <request-id>` returns `CAPABILITY_PENDING` until
   quota qualification is recorded. Otherwise it persists `SEND_UNCERTAIN`
   and returns the native action, thread ID and exact prompt.
3. Call `send_message_to_thread` using that exact target and prompt once.
   An accepted send may remain queued until the chat is opened. Read the same
   chat before retrying; never assume acknowledgement proves a completed reply.
4. Use `read_thread` with enough output capacity. Save its returned JSON,
   including message IDs and truncation flags, then run `reconcile --request-id
   <id> --snapshot-file <file>`. Continue pagination if the anchor is absent.
5. Record `reconcile --request-id <id> --decision adopt|defer|reject --reason
   <reason>`. A complete anchored reply remains useful without a perfect footer.

Different targets, changed payloads, wrong reply IDs, advisor tool/task activity
and partial output do not authorize retransmission. Rate limits, login failure
or generation in progress leave the original request pending; retry reads after
the cooldown, not sends. Continue independent research. Plain Chat currently
cannot directly read Windows files; code is included with content hashes.

Daily requests are reserved once per Tokyo date after 10:00, including weekends.
Distinct on-demand questions are allowed. Identical content is deduplicated.
Do not send catch-up consultations for missed days. No substantive question
means no request. A pending request is reconciled before another is prepared.

The user subsequently selected a fresh fixed-URL Courier fallback because
native extra quota remains unverified. `courier-open` uses the existing Chrome
binary and a fresh project-owned profile under `.local_agent/courier/profile`.
It never imports archived credentials, queues, owner leases or automatic resend.
Install `.[courier]` for Playwright; no additional model/API dependency exists.
`consult --begin-send` returns `courier-send` only after qualification. The driver
persists `SEND_UNCERTAIN` before submission; `courier-read` and an uncertain
`courier-send` are read-only and never resubmit. Target URL, immutable body,
rendered turn and ordinary Chat mode must match. Native and Courier are never
active senders simultaneously; completed native probe evidence stays intact.
Current preflight is `LOGIN_REQUIRED`: no Courier message has been sent.

Official Quick chat documentation establishes an ordinary Chat surface, but
does not specify billing for the native send-message tool. The account's usage
tool reports the aggregate Codex bucket, not request-level attribution. Native
zero extra usage is therefore unverified. Courier's code has no model/Work
launches; live ordinary Chat mode and a real reply still require acceptance.
Ordinary Chat's own limits or eligible account usage remain applicable whichever
transport sends the question. A fixed URL does not change the destination's
billing rules. See https://learn.chatgpt.com/docs/projects and
https://learn.chatgpt.com/docs/pricing.

## Continuation and user stop

Use one native heartbeat on this same chat, every two hours, with a 10:00 Tokyo
daily consultation handled in the same loop. Do not create a new Agent or Goal,
install a Windows task or overlap an active turn. Enable only after the rollout
gates in `.local_agent/rollout.json` pass. The current request authorizes building
the workflow, not restarting a paused scientific job before those gates pass.

For an explicit user stop, set rollout `user_paused` true, set the advisor
`enabled` false and pause the associated native heartbeat. Do not auto-clear
that state at a later trigger. A user resume restores only qualified behavior.
Keep notifications quiet unless there is a meaningful result, fault or required
decision. The heartbeat itself is local Agent execution and uses its allowance.

## Git delivery

Review outgoing changes, commit a tested checkpoint, then run
`publish --tests <targets>`. The command verifies the exact remote sandbox SHA.
`promote --candidate <full-sha> --tests <targets>` checks the published candidate
and fast-forwards remote master from this same checkout. Neither operation
needs a sibling directory or Chat approval. Never force-push.

## Archive and rollback

Tar packages, per-file manifests and extraction verification live under
`E:\CodexArchive\20261003-rebuild`. ACL-preserving GenericChess and retired App
originals live under `C:\Users\wdai\CodexRetired\20261003-rebuild`; their 23 Git
worktree paths were repaired after relocation. Existing CodexRecovery backups
are untouched. Restore old worktrees to their documented layout, or repair
their Git pointers after restoring copies. Never import old App databases,
auth files, Goals or queues into the running fresh installation. Sensitive App
archives must stay user-restricted and must not be attached to Chat or Git.
