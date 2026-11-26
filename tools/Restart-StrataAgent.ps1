& (Join-Path $PSScriptRoot 'Stop-StrataAgent.ps1')
Start-Sleep -Seconds 2
& (Join-Path $PSScriptRoot 'Start-StrataAgent.ps1')
