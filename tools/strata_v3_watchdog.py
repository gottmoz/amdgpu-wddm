"""Restart only the worker identified by a validated Strata V3 profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

try:
    from .strata_v3 import prepare_worker, ROOT
except ImportError:  # Direct script execution places tools/ on sys.path.
    from strata_v3 import prepare_worker, ROOT


def is_owned_worker_command(command, profile_path):
    if not isinstance(command, (list, tuple)):
        return False
    has_entrypoint = any(Path(str(token)).name.casefold() == "strata_v3.py" for token in command)
    profile = Path(profile_path).resolve()
    for index, token in enumerate(command[:-1]):
        if str(token).casefold() == "--profile":
            try:
                return has_entrypoint and Path(str(command[index + 1])).resolve() == profile
            except (OSError, ValueError):
                return False
    return False


def worker_alive(pid, profile_path):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        import psutil
    except ImportError:
        return False
    try:
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE and is_owned_worker_command(
            process.cmdline(), profile_path)
    except psutil.Error:
        return False


def should_start(previous_pid, *, worker_alive, stop_requested):
    return not stop_requested and not worker_alive


def is_recovery(previous_pid, *, worker_alive):
    return isinstance(previous_pid, int) and previous_pid > 0 and not worker_alive


def read_pid(path):
    try:
        return int(Path(path).read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return 0


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def start_worker(profile, profile_path, previous_pid, recovering):
    stop_path = profile.paths["stop"]
    stop_path.unlink(missing_ok=True)
    log_path = profile.paths["log_dir"] / "worker.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log_file:
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "tools" / "strata_v3.py"), "--profile", str(profile_path),
             "--poll-seconds", "30", "--heartbeat-seconds", "60"],
            cwd=profile.worktree,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    profile.paths["worker_pid"].write_text(str(process.pid), encoding="ascii")
    if recovering:
        recovery = {"automatic_recoveries": 0}
        if profile.paths["recoveries"].exists():
            try:
                recovery.update(json.loads(profile.paths["recoveries"].read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                pass
        recovery["automatic_recoveries"] = int(recovery.get("automatic_recoveries", 0)) + 1
        recovery["last_restart_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save_json(profile.paths["recoveries"], recovery)
    return process.pid


def watch(profile_path, *, poll_seconds=10):
    profile = prepare_worker(profile_path)
    pid_path = profile.paths["worker_pid"]
    watchdog_pid_path = profile.paths["watchdog_pid"]
    watchdog_pid_path.write_text(str(__import__("os").getpid()), encoding="ascii")
    try:
        while not profile.paths["stop"].exists():
            previous_pid = read_pid(pid_path)
            alive = worker_alive(previous_pid, profile_path)
            if previous_pid and not alive and _pid_exists(previous_pid):
                raise RuntimeError("worker PID is owned by another process; refusing to replace it")
            if should_start(previous_pid, worker_alive=alive, stop_requested=profile.paths["stop"].exists()):
                start_worker(profile, Path(profile_path).resolve(), previous_pid,
                             is_recovery(previous_pid, worker_alive=alive))
            time.sleep(max(1, poll_seconds))
    finally:
        watchdog_pid_path.unlink(missing_ok=True)


def _pid_exists(pid):
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--poll-seconds", type=int, default=10)
    args = parser.parse_args(argv)
    watch(args.profile, poll_seconds=args.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
