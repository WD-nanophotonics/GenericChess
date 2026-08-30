# GenericChess workflow

Use the `sandbox` worktree for all changes. `master` is the accepted version
and changes only through an authorized fast-forward promotion. A checkpoint is
real only after it is tested, committed, pushed to `origin/sandbox`, and the
local and remote full SHAs match.

The user is always the highest authority. In Courier mode, the current
receipt-bound Chat work order is the next authority, followed by the local
Agent and repository hygiene defaults. Start one mode and keep it for the
whole task.

## Authority and artifact publication

Local `.gitignore` entries and “generated/raw/transient evidence stays out of
Git” rules are defaults for unrequested files, not publication vetoes. When
the user or the current Chat work order names an exact file for upload, commit,
or push, that instruction wins. Preserve the exact generated file, include it
in the checkpoint, and use `git add -f <path>` if needed. The exception is
path-specific: never widen it to an entire output directory or unrelated
artifacts.

The review control chain is therefore:

```text
Chat names exact artifact
→ generate or preserve that artifact
→ run required tests and inspect the exact path
→ stage it (force-add only when the named path is ignored)
→ commit and publish origin/sandbox
→ verify local == remote full SHA
→ close out with that exact SHA
```

An older ADR or local exclusion remains historical context unless the active
Chat work order explicitly changes the handling for its named artifact. The
Agent must still preserve sandbox-only scope, avoid production changes outside
the work order, and never substitute a different transport or a broader file
selection.

## Courier mode

Authority is user, then the current Chat work order, then the local Agent and
its repository defaults.

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

On a Courier error, follow the printed `NEXT_ACTION`. Resume only the same
request. Login, target, access, or uncertain-send errors require the user; they
never authorize a different transport or request.
