# GenericChess

Deterministic rules, immutable game core, generic search, CLI and desktop UI for
chess- and shogi-like games. Native C runtime/search is optional. Research remains
open; development measurements do not establish general amateur strength.

## Run

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,gui]"
.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.venv\Scripts\python.exe -m generic_chess.ui
```

The default tests cover product, current development, workflow and specification;
old experiment receipts are archived rather than collected as product tests.

## Entry points

- [Repository layout](docs/operations/REPOSITORY_LAYOUT.md): code, tests, evidence and recovery.
- [Research mainline](docs/research/LOCAL_MAINLINE.md): current objective and evidence.
- [Chess comparison](docs/research/CHESS_DEVELOPMENT.md): executable development route.
- [Agent policy](AGENTS.md) and [manual](docs/operations/LOCAL_AGENT.md): canonical workflow.
- [Slack workflow](docs/operations/SLACK_WORKFLOW.md): dot consultation and delivery records.
- [Archive index](docs/archive/HISTORY.md): historical material, not a task queue.

One local Agent works on sandbox. A single native90-minute heartbeat resumes the
same chat. Git is version control and final delivery; current public push is held.
No Goal, legacy Courier/worker flow or other project access is part of this route.
