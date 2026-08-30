# GenericChess

GenericChess is a deterministic engine and desktop application for generated
chess- and shogi-like games. It contains a rule compiler, immutable game core,
session and replay APIs, CLI and PySide6 UI, generic AlphaBeta players,
learning experiments, and an optional native C search/runtime backend.

The repository has exactly two product branches:

- `master` is the accepted production baseline. It is never edited directly.
- `sandbox` is the only development branch. Completed work is committed,
  tested, and pushed before it is reviewed or reported.

See [WORKFLOW.md](WORKFLOW.md) for the authority and promotion rules. Historical
audit material removed from the live tree remains available through Git history
and the index in [docs/archive/HISTORY.md](docs/archive/HISTORY.md).

Courier/Chat is also the authoritative review channel for receipt-bound work.
When a Chat work order names a generated report, fixture, or other exact
artifact, that file is a first-class checkpoint deliverable even if the local
repository defaults normally exclude that category. The exception is limited
to the named path; unrelated generated output remains excluded.

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

## Workflow control

```powershell
generic-chess-flow.cmd status
generic-chess-flow.cmd start --mode local
generic-chess-flow.cmd heavy -- .venv\Scripts\python.exe -m generic_chess.learning.experiment --help
generic-chess-flow.cmd publish --tests tests/test_session.py tests/test_ai_search.py
generic-chess-flow.cmd finish
```

Courier-driven work uses `start --mode courier`, `resume`, and `closeout`. The
project control layer delegates transport to the sibling ChatCourier checkout;
it does not use Gmail or directly automate a browser. A Chat-directed artifact
must be tested, committed, pushed to `origin/sandbox`, and reported by its
exact full SHA; `.gitignore` is not a veto for that named deliverable.
