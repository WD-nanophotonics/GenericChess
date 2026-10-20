@echo off
setlocal EnableExtensions
set "DEV_AUX_ROOT=%~dp0"
cd /d "%DEV_AUX_ROOT%"
if /i "%~1"=="publish" (
  >&2 echo DEV_AUX_ROUTE_ERROR: inherited publish targets PRIMARY branches. Review/tests then git push origin sidemission.
  exit /b 2
)
if /i "%~1"=="promote" (
  >&2 echo DEV_AUX_ROUTE_ERROR: inherited promote targets PRIMARY branches. Review/tests then git push origin sidemission.
  exit /b 2
)
if exist "%DEV_AUX_ROOT%.venv\Scripts\python.exe" (
  "%DEV_AUX_ROOT%.venv\Scripts\python.exe" -m tools.local_agent.cli %*
) else (
  "C:\Users\wdai\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m tools.local_agent.cli %*
)
exit /b %ERRORLEVEL%
