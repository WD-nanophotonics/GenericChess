# GenericChess workflow

## Repository topology

The repository has two active branches and two Windows worktrees:

- `master` / `GenericChess`: accepted production baseline; never edit here.
- `sandbox` / `GenericChess-sandbox`: the only editable product worktree.

Both branches track the same-named branch on `origin`. A task is not delivered
until its worktree is clean and local HEAD equals the remote HEAD. `master` must
always be an ancestor of `sandbox`. Promotion is an exact fast-forward of a
tested sandbox HEAD; cherry-picking and force-pushing are forbidden.

Use `generic-chess-flow.cmd` for status, publication, Courier recovery, and
promotion. The installed pre-push hook rejects unsupported branches, direct
master pushes, direct sandbox pushes, and non-fast-forward updates.

## Authority modes

Each task starts in exactly one mode. The user is always the highest authority.

### Courier mode

Authority order is user, the current ChatGPT work order, then the local Agent.
Chat receives only committed, pushed sandbox SHAs. The Agent implements the
authorized scope, tests it, commits it, publishes it, and reports the resulting
full SHA through ChatCourier. A master promotion requires the latest Chat reply
to approve that exact SHA with:

```text
GENERICCHESS_STATUS=CONTINUE|COMPLETE|BLOCKED
GENERICCHESS_CANDIDATE_SHA=<40-hex-sha-or-NONE>
GENERICCHESS_PROMOTION=APPROVE|HOLD
```

ChatCourier is transport only. The project uses its typed prepare, dispatch,
status, and recovery operations. Do not use Gmail, directly control Chrome,
change the registered URL/profile, or replace an uncertain request.

### Local mode

Authority order is user, then the local Agent. Courier is not consulted and its
availability cannot block work. After review and test gates pass, the local
Agent may authorize promotion of the synchronized sandbox HEAD.

## Standard commands

```powershell
generic-chess-flow.cmd status
generic-chess-flow.cmd start --mode courier --message-file <request.txt>
generic-chess-flow.cmd start --mode local
generic-chess-flow.cmd publish --tests <pytest-target> [...]
generic-chess-flow.cmd resume
generic-chess-flow.cmd closeout --report-file <report.txt>
generic-chess-flow.cmd promote --candidate <full-sandbox-sha>
generic-chess-flow.cmd finish
```

Edits may exist while an Agent is actively working, but a checkpoint, report,
handoff, or completion is valid only after commit, `publish`, and SHA
verification. Do not mix Courier and local authority within one active session.
