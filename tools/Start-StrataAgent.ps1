$ErrorActionPreference='Stop'
$runtime=if($env:STRATA_RUNTIME_DIR){$env:STRATA_RUNTIME_DIR}else{'D:\BC250-Development\scratch\strata-runtime'}
New-Item -ItemType Directory -Path $runtime -Force|Out-Null
$pidFile=Join-Path $runtime 'agent.pid'
if(Test-Path $pidFile){$id=[int](Get-Content $pidFile -Raw); if(Get-Process -Id $id -ErrorAction SilentlyContinue){Write-Output "running pid=$id"; exit 0}}
$root=Split-Path -Parent $PSScriptRoot
$python=(Get-Command python).Source
$p=Start-Process -FilePath $python -ArgumentList @((Join-Path $PSScriptRoot 'strata_daemon.py')) -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'agent.out.log') -RedirectStandardError (Join-Path $runtime 'agent.err.log')
$p.Id|Set-Content $pidFile
Write-Output "started pid=$($p.Id)"
