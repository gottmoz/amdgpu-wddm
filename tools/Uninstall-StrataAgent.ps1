Unregister-ScheduledTask -TaskName 'BC250-Strata-Agent' -Confirm:$false -ErrorAction SilentlyContinue
& (Join-Path $PSScriptRoot 'Stop-StrataAgent.ps1')
