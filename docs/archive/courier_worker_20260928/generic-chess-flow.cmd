@echo off
setlocal EnableExtensions
set "GC_ROOT=%~dp0"
if exist "%GC_ROOT%.venv\Scripts\python.exe" (
  "%GC_ROOT%.venv\Scripts\python.exe" "%GC_ROOT%tools\generic_chess_flow.py" %*
) else (
  py -3 "%GC_ROOT%tools\generic_chess_flow.py" %*
)
exit /b %ERRORLEVEL%
