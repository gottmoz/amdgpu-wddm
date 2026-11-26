"""Restart only the Strata daemon process launched by this installation."""
import os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=Path(os.environ.get('STRATA_RUNTIME_DIR',r'D:\BC250-Development\scratch\strata-runtime'))
PID=RUNTIME/'v2-daemon.pid'; STOP=RUNTIME/'STRATA_STOP'; OUT=RUNTIME/'v2-daemon.out.log'; ERR=RUNTIME/'v2-daemon.err.log'
CHECK=30

def alive(pid):
    try:
        import psutil
        p=psutil.Process(pid)
        return p.is_running() and 'strata_daemon.py' in ' '.join(p.cmdline())
    except Exception: return False

def start():
    STOP.unlink(missing_ok=True)
    env=os.environ.copy(); env['STRATA_RUNTIME_DIR']=str(RUNTIME); env.setdefault('BC250_ROOT',r'D:\BC250-Development')
    with OUT.open('ab') as stdout, ERR.open('ab') as stderr:
        p=subprocess.Popen([sys.executable,str(ROOT/'tools/strata_daemon.py'),'--poll-seconds','30','--heartbeat-seconds','60'],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    PID.write_text(str(p.pid)); return p.pid

while not STOP.exists():
    try:
        pid=int(PID.read_text()) if PID.exists() else 0
        if not pid or not alive(pid): start()
    except Exception as exc:
        with ERR.open('a',encoding='utf-8') as f: f.write(f'watchdog {time.time()}: {exc}\n')
    time.sleep(CHECK)
