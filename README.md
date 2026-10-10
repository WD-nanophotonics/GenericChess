# GenericChess UI Test

UI-only development branch with a complete frozen AI backend for PVE.
See [UI Test handoff](docs/ui/UI_TEST.md) for scope, interfaces and merge guidance.

## Start on another computer (Windows, Python 3.11 or newer)

```powershell
git clone --branch ui-test --single-branch https://github.com/WD-nanophotonics/GenericChess.git
cd GenericChess
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[gui]" pytest
.venv\Scripts\python.exe run_ui.py
```

In New Match choose built-in Chess or Shogi, or a generated ruleset, then choose
Human/AI sides. For responsive UI work choose fixed-time thinking around1second.
The startup board alone is not a PVE match until New Match participants are set.
Use run_ui.bat after installation. No cshogi, Zig, native DLL, research dataset,
local-agent state or Slack account is needed. The C extension is optional;
this branch's UI player explicitly uses Python Core even if one is installed.

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/product/test_ui_test_pve.py tests/product/test_ui_controller.py tests/product/test_ui_lifecycle.py tests/product/test_ui_app.py
```

Develop UI here; sandbox continues independent engine research. Do not merge
sandbox repeatedly into this branch or repair/retrain its AI for UI development.
The AI's strength is not an acceptance condition; legal PVE operation is.
