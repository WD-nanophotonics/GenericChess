@echo off
setlocal
"%~dp0.venv\Scripts\python.exe" "%~dp0.local_agent\deepseek-runtime\start.py" %*
exit /b %ERRORLEVEL%
