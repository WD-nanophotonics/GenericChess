# GenericChess

Deterministic rules, a complete game-state core, generic search and learning,
CLI and desktop UI for chess- and shogi-like generated games. Native search is
optional. General playing strength remains an open research question.

## Run

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,gui]"
.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.venv\Scripts\python.exe -m generic_chess.ui
```

## Project entries

- [Current research](docs/research/LOCAL_MAINLINE.md)
- [Code, tests and recovery](docs/operations/REPOSITORY_LAYOUT.md)
- [Policy](AGENTS.md), [local operations](docs/operations/LOCAL_AGENT.md) and [Slack reads](docs/operations/SLACK_WORKFLOW.md)
- [Cleanup record](docs/operations/CLEANUP_20261021.md)

This checkout owns DEV_AUX / sidemission. The existing hourly patrols keep their current
recurrence. Git publication remains authorized to the assigned branch. Slack
uses the periodic Chat mailbox protocol; there is no real-time Dot contact.
The bounded cleanup was read-only. Uncertain delivery is reconciled by a later
read, never by an automatic resend.
Closed experiment payloads are recovered from pinned Git history rather than
restored wholesale into the working tree. Current dependencies remain local.
