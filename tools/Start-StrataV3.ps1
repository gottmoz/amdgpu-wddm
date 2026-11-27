param(
    [Parameter(Mandatory = $true)]
    [string]$Profile,
    [int]$ReadyTimeoutSeconds = 15
)

$ErrorActionPreference = 'Stop'
$profilePath = (Resolve-Path -LiteralPath $Profile).Path
$profileData = Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
$runtimeDir = [System.IO.Path]::GetFullPath($profileData.runtime_dir)
$watchdogPidPath = Join-Path $runtimeDir $profileData.paths.watchdog_pid
$workerPidPath = Join-Path $runtimeDir $profileData.paths.worker_pid
$stopPath = Join-Path $runtimeDir $profileData.paths.stop
$python = (Get-Command python -ErrorAction Stop).Source
$watchdog = Join-Path $PSScriptRoot 'strata_v3_watchdog.py'

if (Test-Path -LiteralPath $watchdogPidPath) {
    $existingId = [int](Get-Content -LiteralPath $watchdogPidPath -Raw)
    if (Get-Process -Id $existingId -ErrorAction SilentlyContinue) {
        Write-Output "watchdog already running pid=$existingId"
        exit 0
    }
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
Remove-Item -LiteralPath $stopPath -Force -ErrorAction SilentlyContinue
$logPath = Join-Path $runtimeDir 'watchdog.log'
$errorLogPath = Join-Path $runtimeDir 'watchdog.err.log'
$process = Start-Process -FilePath $python -ArgumentList @(
    $watchdog, '--profile', $profilePath
) -WorkingDirectory $profileData.worktree -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $logPath -RedirectStandardError $errorLogPath

$deadline = [DateTime]::UtcNow.AddSeconds([Math]::Max(1, $ReadyTimeoutSeconds))
do {
    Start-Sleep -Milliseconds 250
    if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
        throw "Strata V3 watchdog exited during startup; inspect $logPath"
    }
    if ((Test-Path -LiteralPath $watchdogPidPath) -and (Test-Path -LiteralPath $workerPidPath)) {
        Write-Output "started watchdog pid=$($process.Id); worker pid=$((Get-Content -LiteralPath $workerPidPath -Raw).Trim())"
        exit 0
    }
} while ([DateTime]::UtcNow -lt $deadline)

throw "Strata V3 startup was not confirmed; inspect $logPath"
