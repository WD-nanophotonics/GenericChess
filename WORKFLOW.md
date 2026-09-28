# GenericChess workflow quick reference

Policy and authority live only in `AGENTS.md`. This file lists normal commands.

```powershell
generic-chess-flow.cmd status
generic-chess-flow.cmd work
generic-chess-flow.cmd followup --message-file <path> [--reviewed-local-only | --scope-reply-local-only | --phase-complete-local-only | --decision-reply-local-only]
generic-chess-flow.cmd publish --tests <pytest-target> [...]
generic-chess-flow.cmd closeout --report-file <path> [--local-only] [--attachment <path>]
generic-chess-flow.cmd recover
generic-chess-flow.cmd heavy --resource-envelope <path> -- <command>
generic-chess-flow.cmd heavy-start --label <label> --resource-envelope <path> -- <command>
generic-chess-flow.cmd heavy-status [--run-id <id>]
generic-chess-flow.cmd supervisor-patrol --issue-key <fingerprint> --progress-key <evidence> --worker-state <state> --goal-state <active|paused|blocked|unknown> [--action <repair>]
generic-chess-flow.cmd supervisor-hold --reason-file <path>
generic-chess-flow.cmd supervisor-release --hold-id <id> --detail-file <path>
generic-chess-flow.cmd promote --candidate <full-sandbox-sha>
```

`work` resumes the current Courier request or obtains the next order. Read
captured `CONTINUE` prose even without `WORK_ORDER_ID`: a clearly bounded
mainline task may proceed under `AGENTS.md`; a direction-only reply uses the
documented decision followup. The missing ID alone is not a stop.
`followup --reviewed-local-only` is for the registered Supervisor after a
reconciled, unpublished local closeout received only a local-review notice.
It verifies the prior response, unchanged remote SHA, and local commit ancestry,
then records the old/new Courier request lineage without publishing the commit.
`followup --scope-reply-local-only` lets the Worker report a Supervisor-declined
scope after a reconciled local-only closeout reply. It requires the matching
completed receipt and keeps the local candidate unpublished.
`followup --phase-complete-local-only` requests the next order after Chat marks
one local-only phase COMPLETE without explicitly completing the whole project.
`followup --decision-reply-local-only` sends a Supervisor direction decision
after a reconciled local-only CONTINUE reply that contains no executable order.
It keeps the candidate unpublished and records the prior request and reply hash.
`recover` reconciles that same request. Heavy uses only its declared envelope.
Publish tested project checkpoints by default and give Chat the verified
`origin/sandbox` SHA. The user's project-data authorization supersedes a
routine Chat `LOCAL_ONLY` label; document the change in the closeout. Use
`closeout --local-only` only for a specific user prohibition or unresolved
personal/sensitive-content concern; its report must identify the unpublished
local SHA. See `AGENTS.md` for policy.
`supervisor-patrol` compares the current observation with the prior hourly
observation; see `docs/operations/WORKFLOW_RECOVERY.md` for evidence rules.
The retired
`compute-plan-request`, `compute-plan-approve`, `compute-plan-status`, and
`compute-plan-revoke` commands are removed from the normal workflow.
