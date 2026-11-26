$runtime=if($env:STRATA_RUNTIME_DIR){$env:STRATA_RUNTIME_DIR}else{'D:\BC250-Development\scratch\strata-runtime'}
New-Item -ItemType File -Path (Join-Path $runtime 'STRATA_STOP') -Force|Out-Null
$pidFile=Join-Path $runtime 'agent.pid'
if(Test-Path $pidFile){$id=[int](Get-Content $pidFile -Raw); try{Wait-Process -Id $id -Timeout 15 -ErrorAction Stop}catch{}}
