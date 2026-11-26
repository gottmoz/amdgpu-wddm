param([switch]$EnableAtLogon)
$ErrorActionPreference='Stop'
$action=New-ScheduledTaskAction -Execute 'pwsh.exe' -Argument "-NoProfile -File `"$PSScriptRoot\Start-StrataAgent.ps1`""
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
Register-ScheduledTask -TaskName 'BC250-Strata-Agent' -Action $action -Trigger $trigger -Description 'Start the local BC-250 Strata coordinator at user logon.' -Force | Out-Null
if($EnableAtLogon){Enable-ScheduledTask -TaskName 'BC250-Strata-Agent'|Out-Null}else{Disable-ScheduledTask -TaskName 'BC250-Strata-Agent'|Out-Null}
