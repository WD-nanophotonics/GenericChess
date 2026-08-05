@echo off
rem Double-click fallback launcher for the GenericChess desktop UI.
cd /d "%~dp0"
".venv\Scripts\python.exe" run_ui.py %*
if errorlevel 1 pause
