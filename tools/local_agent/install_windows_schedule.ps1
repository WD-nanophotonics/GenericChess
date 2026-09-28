param(
    [Parameter(Mandatory = $true)][string]$ThreadId,
    [string]$TaskName = 'GenericChess-Local-Agent-Two-Hour'
)

$ErrorActionPreference = 'Stop'
if ($ThreadId -notmatch '^[0-9a-f-]{36}$') { throw 'A registered Codex thread UUID is required.' }
$repository = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$codex = (Get-Command codex -ErrorAction Stop).Source
$stateDirectory = Join-Path $repository '.local_agent'
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
@{ codex_path = $codex; thread_id = $ThreadId } | ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $stateDirectory 'windows_schedule.json') -Encoding utf8

$runner = Join-Path $PSScriptRoot 'run_scheduled_turn.ps1'
$arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}"' -f $runner
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $repository
$today = (Get-Date).Date
$triggers = @(0..11 | ForEach-Object {
    New-ScheduledTaskTrigger -Daily -At $today.AddHours($_ * 2).AddMinutes(18)
})
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Description 'Queue one ordinary work turn to the same GenericChess local Agent every two hours.' -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName,State
Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object LastRunTime,NextRunTime,LastTaskResult
