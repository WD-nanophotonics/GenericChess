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

### Continuation invariant

The lifecycle is `work order active → checkpoint published → closeout sent →
CONTINUE/next work order`, which returns to `work order active`. Closeout is a
handoff event, not a terminal event. `COMPLETE` or genuine `BLOCKED` is the
only Courier response that may enter terminal reconciliation. A queue wait,
successful checkpoint, phase boundary, or failed gate with another safe order
is not permission to stop. While `CONTINUE` or `WORK_ORDER_ID` is present, the
Agent must continue the same immutable request, must not call `finish`, and
must not send a final response or create a replacement request. The flow
script independently rejects `finish` in this state.

Courier is only transport. While waiting, its queue events are printed live;
`queue_waiting` means keep waiting, not start another request. `resume` always
uses the same immutable request. Never use Gmail, another browser/profile, a
replacement request, WSL, or a background Courier process.

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
generic-chess-flow.cmd resume
generic-chess-flow.cmd closeout --report-file <path>
generic-chess-flow.cmd promote --candidate <full-sandbox-sha>
generic-chess-flow.cmd finish
```

Run long tests, self-play, benchmarks, and large audits through `heavy`. It runs
one GenericChess compute task at a time at Windows Below Normal priority.
`publish` applies the same rule to pytest automatically.

Before a final response, verify: the latest control footer is terminal, no
work order is active, no Courier request needs reconciliation, and the latest
published sandbox SHA is known and synchronized. `BLOCKED` is reserved for a
hard error or genuinely required user/external action.

On a Courier error, follow the printed `NEXT_ACTION`. Resume only the same
request. Login, target, access, or uncertain-send errors require the user; they
never authorize a different transport or request.
