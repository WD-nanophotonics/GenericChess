@echo off
cd /d "%~dp0"
if exist ".web-venv\Scripts\python.exe" (
  ".web-venv\Scripts\python.exe" run_web.py %*
) else (
  ".venv\Scripts\python.exe" run_web.py %*
)
if errorlevel 1 pause
