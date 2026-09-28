@echo off
setlocal EnableExtensions
set "GC_ROOT=%~dp0"
cd /d "%GC_ROOT%"
if exist "%GC_ROOT%.venv\Scripts\python.exe" (
  "%GC_ROOT%.venv\Scripts\python.exe" -m tools.local_agent.cli %*
) else (
  py -3 -m tools.local_agent.cli %*
)
exit /b %ERRORLEVEL%
