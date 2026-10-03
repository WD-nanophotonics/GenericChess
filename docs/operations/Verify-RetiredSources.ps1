# Run manually in an Administrator PowerShell. Read/copy only; never deletes
# source data, changes ACLs, launches project jobs, or enables automation.
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this read-only recovery capture from an Administrator PowerShell.'
}
$sourceParent = 'C:\Users\wdai\Documents\ChatGPT'
$archiveParent = [IO.Path]::GetFullPath('E:\CodexArchive\20261003-rebuild')
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$capture = [IO.Path]::GetFullPath((Join-Path $archiveParent ('admin-capture-' + $stamp)))
if (-not $capture.StartsWith($archiveParent + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid capture path' }
if (Test-Path -LiteralPath $capture) { throw 'Capture already exists; nothing will be overwritten' }
New-Item -ItemType Directory -Path $capture | Out-Null
$records = @()
foreach ($name in @('GenericChess', 'GenericChess-sandbox')) {
    $source = [IO.Path]::GetFullPath((Join-Path $sourceParent $name))
    $target = Join-Path $capture $name
    if ([IO.Path]::GetDirectoryName($source) -ne $sourceParent) { throw 'Unexpected source root' }
    # /B uses backup-read privilege for historical ACL-protected evidence.
    # /XJ avoids following junctions; neither /MOVE, /MIR nor /PURGE is used.
    & robocopy.exe $source $target /B /E /XJ /COPY:DAT /DCOPY:DAT /R:0 /W:0 /NFL /NDL /NP /NJH /NJS
    $code = $LASTEXITCODE
    $records += @{Source=$source; Capture=$target; RobocopyExitCode=$code}
    $records | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $capture 'CAPTURE_REPORT.json') -Encoding utf8
    if ($code -ge 8) { throw 'Capture is incomplete; retain it and the source for diagnosis.' }
}
Write-Output ('Read-only administrator capture completed: ' + $capture)
Write-Output 'Originals remain in place. Rehash the captured files and repair/archive worktree metadata before authorizing a move.'
