$runtime=if($env:STRATA_RUNTIME_DIR){$env:STRATA_RUNTIME_DIR}else{'D:\BC250-Development\scratch\strata-runtime'}
$pidFile=Join-Path $runtime 'agent.pid'; $id=if(Test-Path $pidFile){[int](Get-Content $pidFile -Raw)}else{$null}
$p=if($id){Get-Process -Id $id -ErrorAction SilentlyContinue}else{$null}
[pscustomobject]@{State=if($p){'running'}else{'stopped'};Pid=$id;Runtime=$runtime;LastCheckpoint=(Get-Item (Join-Path $runtime 'STRATA_CHECKPOINT.json') -ErrorAction SilentlyContinue).LastWriteTime;LastError=(Get-Content (Join-Path $runtime 'STRATA_DAEMON_ERROR.txt') -Tail 1 -ErrorAction SilentlyContinue)}
