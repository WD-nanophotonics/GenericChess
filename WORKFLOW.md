# GenericChess workflow

Use the `sandbox` worktree for all changes. `master` is the accepted version
and changes only through an authorized fast-forward promotion. A checkpoint is
real only after it is tested, committed, pushed to `origin/sandbox`, and the
local and remote full SHAs match.

The user is always the highest authority. Start one mode and keep it for the
whole task.

## Courier mode

Authority is user, then the current Chat work order, then the local Agent.

The normal bootstrap is simply:

```text
User: 开始工作
Agent: switch to GenericChess-sandbox and run generic-chess-flow.cmd work
```

`work` starts Courier with a built-in request, resumes the same interrupted
request, or redisplays the current work order. It never creates a replacement
for an active request. The Agent keeps following the loop below in the same
turn until Chat returns `COMPLETE` or `BLOCKED`, a hard error needs the user, or
the user stops it.

```text
start --mode courier --message-file <request>
→ follow the returned work order without expanding it
→ edit and test
→ commit
→ publish --tests <pytest targets>
→ closeout --report-file <report>
→ continue with the next work order, or finish after COMPLETE/BLOCKED
```

Courier is only transport. While waiting, its queue events are printed live;
`queue_waiting` means keep waiting, not start another request. `recover`
(`resume` is a compatibility alias) always starts with the read-only
`capture_latest` probe against the same immutable request. It then follows this
bounded recovery ladder:

```text
matching reply → import and continue
request exists without reply → recover/wait
request absent + fresh safe evidence → retry the immutable request once
evidence conflict or recovery failure → Supervisor escalation
Supervisor cannot safely resolve → HUMAN_REQUIRED
```

Transport, browser, network, and timeout failures are `RECOVERING` or
`ESCALATED`, never fabricated Chat `BLOCKED` decisions. Automatic evidence
retry has a budget of one per immutable request. A true `resend_once` requires
the registered Supervisor to claim the escalation. Never use Gmail, another
browser/profile, a replacement request, WSL, or a background Courier process.

The worker records its `CODEX_THREAD_ID` in the escalation dossier. The current
management task is registered as Supervisor by its `CODEX_THREAD_ID`, not its
title. The worker sends the dossier notification directly to that task. There
is no transport-recovery polling heartbeat: completion and escalation handoffs
are direct task messages. A separate hourly management heartbeat may audit
progress and wake an unjustifiably idle worker, but it never replaces Courier or
creates another writer. While an escalation or Supervisor HOLD is active, the
worker must stop repository writes. The Supervisor
may diagnose transport/framework state, repair within the original authority,
or review the sole `resend_once`; it may not expand the work order, change the
Chat target, delete unknown data, or promote `master`. A signed resolution must
name the original worker task so execution returns to the same task and request.

The registered Supervisor may place an urgent HOLD for execution drift that is
not a Courier transport failure. HOLD is runtime-only and blocks work/start,
heavy commands, commits, pushes, publish, closeout, promotion, and finish. The
same Supervisor must record a hashed release before the original worker resumes.
Normal review feedback is queued to the worker without a HOLD.

Chat may approve promotion only for the exact pushed sandbox SHA using:

```text
GENERICCHESS_STATUS=CONTINUE|COMPLETE|BLOCKED
GENERICCHESS_CANDIDATE_SHA=<40-hex-sha-or-NONE>
GENERICCHESS_PROMOTION=APPROVE|HOLD
```

## Local mode

Authority is user, then the local Agent. Courier is never consulted.

```text
start --mode local
→ edit and test
→ commit
→ publish --tests <pytest targets>
→ optionally promote --candidate <full-sandbox-sha>
→ finish
```

## Commands

```powershell
generic-chess-flow.cmd status
generic-chess-flow.cmd work
generic-chess-flow.cmd start --mode courier|local [--message-file <path>]
generic-chess-flow.cmd heavy -- <long-running command>
generic-chess-flow.cmd publish --tests <pytest-target> [...]
generic-chess-flow.cmd recover [--worker-thread-id <CODEX_THREAD_ID>]
generic-chess-flow.cmd resume
generic-chess-flow.cmd register-supervisor [--thread-id <CODEX_THREAD_ID>]
generic-chess-flow.cmd register-worker --thread-id <CODEX_THREAD_ID>
generic-chess-flow.cmd supervisor-hold --reason-file <path> [--worker-thread-id <id>]
generic-chess-flow.cmd supervisor-hold-status [--check-write]
generic-chess-flow.cmd supervisor-release --hold-id <id> --detail-file <path>
generic-chess-flow.cmd escalate --reason <text> [--worker-thread-id <id>]
generic-chess-flow.cmd supervisor-pending  # manual diagnostic only
generic-chess-flow.cmd supervisor-claim --escalation-id <id>
generic-chess-flow.cmd supervisor-resend --escalation-id <id>
generic-chess-flow.cmd supervisor-resolve --escalation-id <id> --action RESUME_WORKER|RECOVERED|USER_SUPERSEDED_REQUEST|HUMAN_REQUIRED [--detail-file <path>]
generic-chess-flow.cmd closeout --report-file <path>
generic-chess-flow.cmd promote --candidate <full-sandbox-sha>
generic-chess-flow.cmd finish
```

Run long tests, self-play, benchmarks, and large audits through `heavy`. It runs
one GenericChess compute task at a time at Windows Below Normal priority.
`publish` applies the same rule to pytest automatically.

On a Courier error, run `recover` for the same request. Login, target, access,
or uncertain external side effects escalate to the Supervisor before they reach
the user; they never authorize a different transport or request.

Only an explicit user instruction may let the claiming Supervisor resolve an
irrecoverable active transport request as `USER_SUPERSEDED_REQUEST`. This keeps
the retired request and dossier as evidence, clears it from the live session,
and lets the same worker task request fresh work without changing authority mode.

Courier messages are intentionally small. If a report exceeds 24 KiB, place the
durable, reviewable report inside the repository, commit it, publish that exact
sandbox SHA, and send only its repository/commit/path reference. An untracked,
unpublished, or modified large local report is rejected before any browser is
opened. Raw transient output still stays out of Git; summarize it into a durable
audit report first.

## Cross-machine ownership

The public `workflow-state` branch is a separate, fast-forward-only control
history. It does not change `master` or `sandbox`. A machine must run
`machine-setup`, then own the latest `CLAIMED` capsule before any mutating flow
command succeeds. Release is allowed only at a clean published checkpoint with
an empty Courier queue and no browser owner. See `MIGRATION.md` for setup and
handoff commands. Chat URLs, browser profiles, credentials, absolute paths, and
Codex task IDs never enter the branch.
