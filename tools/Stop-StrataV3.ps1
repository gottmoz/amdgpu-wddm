param(
    [Parameter(Mandatory = $true)]
    [string]$Profile,
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'
$profilePath = (Resolve-Path -LiteralPath $Profile).Path
$profileData = Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
$runtimeDir = [System.IO.Path]::GetFullPath($profileData.runtime_dir)
$stopPath = Join-Path $runtimeDir $profileData.paths.stop
$watchdogPidPath = Join-Path $runtimeDir $profileData.paths.watchdog_pid
$workerPidPath = Join-Path $runtimeDir $profileData.paths.worker_pid

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
New-Item -ItemType File -Path $stopPath -Force | Out-Null
$deadline = [DateTime]::UtcNow.AddSeconds([Math]::Max(1, $TimeoutSeconds))
while ([DateTime]::UtcNow -lt $deadline) {
    $watchdogId = if (Test-Path -LiteralPath $watchdogPidPath) { [int](Get-Content -LiteralPath $watchdogPidPath -Raw) } else { 0 }
    $workerId = if (Test-Path -LiteralPath $workerPidPath) { [int](Get-Content -LiteralPath $workerPidPath -Raw) } else { 0 }
    $watchdogAlive = $watchdogId -gt 0 -and (Get-Process -Id $watchdogId -ErrorAction SilentlyContinue)
    $workerAlive = $workerId -gt 0 -and (Get-Process -Id $workerId -ErrorAction SilentlyContinue)
    if (-not $watchdogAlive -and -not $workerAlive) {
        Write-Output 'Strata V3 stopped cleanly'
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

throw 'Strata V3 did not stop before timeout; no process was force-terminated'
