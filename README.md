# GenericChess

GenericChess is a deterministic engine and desktop application for generated
chess- and shogi-like games. It contains a rule compiler, immutable game core,
session and replay APIs, CLI and PySide6 UI, generic AlphaBeta players,
learning experiments, and an optional native C search/runtime backend.

The repository has exactly two product branches:

- `master` is the accepted production baseline. It is never edited directly.
- `sandbox` is the development branch. The local Agent decides when a tested
  checkpoint is ready to publish.

See [AGENTS.md](AGENTS.md) for the current authority rules. Historical
audit material removed from the live tree remains available through Git history
and the index in [docs/archive/HISTORY.md](docs/archive/HISTORY.md).

## Setup

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,gui]"
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Run the desktop application with `run_ui.bat`, or use:

```powershell
.venv\Scripts\python.exe -m generic_chess.ui
.venv\Scripts\python.exe -m generic_chess.demo.headless_demo
```

## Local agent workflow

```powershell
generic-chess-local.cmd status
generic-chess-local.cmd patrol
generic-chess-local.cmd consult --question-file <path>
generic-chess-local.cmd publish --tests tests/test_session.py tests/test_ai_search.py
generic-chess-local.cmd promote --candidate <full-sha> --tests <pytest-target>
```

The local Agent makes research and Git decisions. ChatCourier is reused only
for one daily scientific consultation; Chat replies are advisory. See
`AGENTS.md` and `docs/operations/LOCAL_AGENT.md`. The former work-order flow
is archived in `docs/archive/courier_worker_20260928/`.
