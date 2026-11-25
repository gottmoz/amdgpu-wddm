param([int]$RetrySeconds = 10)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

while ($true) {
    $queue = Get-Content (Join-Path $repo 'TASK_QUEUE.json') -Raw | ConvertFrom-Json
    $ready = @($queue.tasks | Where-Object { $_.status -in @('pending', 'running') })
    if ($ready.Count -eq 0) { exit 0 }
    & python (Join-Path $PSScriptRoot 'strata_supervisor.py') --once
    if ($LASTEXITCODE -ne 0) {
        $queue = Get-Content (Join-Path $repo 'TASK_QUEUE.json') -Raw | ConvertFrom-Json
        $ready = @($queue.tasks | Where-Object { $_.status -in @('pending', 'running') })
        if ($ready.Count -eq 0) { exit 1 }
        Start-Sleep -Seconds $RetrySeconds
    }
}
