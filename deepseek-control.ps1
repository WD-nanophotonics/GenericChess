param([ValidateSet('Start','Stop','Status')][string]$Action = 'Start', [switch]$ReplaceKey)
# Optional compatibility entry. Prefer .cmd when PowerShell scripts are disabled.
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$entry = Join-Path $PSScriptRoot '.local_agent/deepseek-runtime/start.py'
if ($ReplaceKey) { & $python $entry $Action --replace-key }
else { & $python $entry $Action }
exit $LASTEXITCODE
