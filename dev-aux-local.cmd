@echo off
setlocal EnableExtensions
set "DEV_AUX_ROOT=%~dp0"
cd /d "%DEV_AUX_ROOT%"
for /f "delims=" %%b in ('git branch --show-current') do set "DEV_AUX_BRANCH=%%b"
if not "%DEV_AUX_BRANCH%"=="sidemission" exit /b 2
if /i "%~1"=="publish" exit /b 2
if /i "%~1"=="promote" exit /b 2
if exist "%DEV_AUX_ROOT%.venv\Scripts\python.exe" (
  "%DEV_AUX_ROOT%.venv\Scripts\python.exe" -m tools.local_agent.cli %*
) else (
  "C:\Users\wdai\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m tools.local_agent.cli %*
)
exit /b %ERRORLEVEL%
