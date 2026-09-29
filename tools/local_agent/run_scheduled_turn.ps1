param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
$repository = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$stateDirectory = Join-Path $repository '.local_agent'
$configurationPath = Join-Path $stateDirectory 'windows_schedule.json'
if (-not (Test-Path -LiteralPath $configurationPath)) {
    throw "Missing local schedule configuration: $configurationPath"
}
$configuration = Get-Content -LiteralPath $configurationPath -Raw | ConvertFrom-Json
$codex = [string]$configuration.codex_path
$threadId = [string]$configuration.thread_id
if (-not (Test-Path -LiteralPath $codex) -or $threadId -notmatch '^[0-9a-f-]{36}$') {
    throw 'The Codex executable or registered thread ID is invalid.'
}

$mutex = [System.Threading.Mutex]::new($false, 'Local\GenericChessSingleScheduledTurn')
$acquired = $false
try {
    $acquired = $mutex.WaitOne(0)
    if (-not $acquired) {
        Write-Output 'An earlier GenericChess schedule check is still running.'
        exit 0
    }
    $tokyo = [System.TimeZoneInfo]::FindSystemTimeZoneById('Tokyo Standard Time')
    $now = [System.TimeZoneInfo]::ConvertTimeFromUtc((Get-Date).ToUniversalTime(), $tokyo)
    $slot = '{0:yyyyMMdd}-{1:D2}' -f $now, ([int]([math]::Floor($now.Hour / 2) * 2))
    $ledgerPath = Join-Path $stateDirectory 'scheduled-last-enqueue.json'
    $ledger = if (Test-Path -LiteralPath $ledgerPath) {
        Get-Content -LiteralPath $ledgerPath -Raw | ConvertFrom-Json
    } else { $null }
    if ($ledger -and $ledger.slot -eq $slot) {
        Write-Output "The $slot scheduled turn was already queued."
        exit 0
    }
    $patrolPath = Join-Path $stateDirectory 'patrol.json'
    $patrol = if (Test-Path -LiteralPath $patrolPath) {
        Get-Content -LiteralPath $patrolPath -Raw | ConvertFrom-Json
    } else { $null }
    $patrolAt = if ($patrol) { [string]$patrol.at } else { $null }
    $needsRecovery = [bool]($ledger -and $ledger.patrol_at_before -eq $patrolAt)
    $prompt = 'Two-hour ordinary-mode continuation in the same GenericChess local Agent task. Do not enable Goal. Read AGENTS.md, .local_agent/NEXT_WORK.md, WORKFLOW.md, docs/operations/LOCAL_AGENT.md, and docs/research/LOCAL_MAINLINE.md. Reconcile unfinished handoff stages with actual results first; if the file is missing, initialize it from the mainline before new research. Run generic-chess-local.cmd patrol --record. Work through useful bounded stages while resources allow, updating the compact handoff after each stage and writing the next batch before new work. A stage or turn boundary is not mainline completion; only sufficient evidence that the mainline objective is complete ends the task. Do not repeat an unsuccessful path without new evidence. Follow the weekday Chat advisory rule if due. Preserve this thread and checkout.'
    if ($needsRecovery) {
        $prompt = 'The previous queued turn has no recorded patrol. First inspect its visible result and record this turn''s patrol; reconcile unfinished work in the same thread. ' + $prompt
    }
    if ($DryRun) {
        Write-Output "Dry run: queue $slot to thread $threadId with $codex (recovery=$needsRecovery)"
        exit 0
    }
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & $codex queue --thread $threadId --message $prompt 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0 -or $output -notmatch 'Queued message ([0-9a-f-]{36})') {
        throw "Codex did not confirm enqueue (exit $exitCode): $output"
    }
    $record = [ordered]@{
        slot = $slot
        queued_at = (Get-Date).ToUniversalTime().ToString('o')
        queue_id = $Matches[1]
        thread_id = $threadId
        patrol_at_before = $patrolAt
        recovery = $needsRecovery
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath $ledgerPath -Encoding utf8
    Write-Output "Queued $slot to the same Agent task: $($record.queue_id) (recovery=$needsRecovery)"
}
finally {
    if ($acquired) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
