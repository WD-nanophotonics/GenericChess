# GenericChess workflow quick reference

Policy and authority live only in `AGENTS.md`. This file lists normal commands.

```powershell
generic-chess-flow.cmd status
generic-chess-flow.cmd work
generic-chess-flow.cmd publish --tests <pytest-target> [...]
generic-chess-flow.cmd recover
generic-chess-flow.cmd heavy --resource-envelope <path> -- <command>
generic-chess-flow.cmd heavy-start --label <label> --resource-envelope <path> -- <command>
generic-chess-flow.cmd heavy-status [--run-id <id>]
generic-chess-flow.cmd supervisor-hold --reason-file <path>
generic-chess-flow.cmd supervisor-release --hold-id <id> --detail-file <path>
generic-chess-flow.cmd promote --candidate <full-sandbox-sha>
```

`work` resumes the current Courier request or obtains the next order.
`recover` reconciles that same request. Heavy uses only its declared envelope;
an optional plan supplies local scientific context. The retired
`compute-plan-request`, `compute-plan-approve`, `compute-plan-status`, and
`compute-plan-revoke` commands are removed from the normal workflow.
