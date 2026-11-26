"""Long-running, review-gated coordinator for the existing Strata supervisor.

Run in a dedicated research worktree. Create STRATA_STOP to shut down cleanly.
GitHub status and inbox live on separate agent/* branches. No main writes.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

import strata_supervisor as worker


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = worker.RUNTIME
INBOX_QUEUE = RUNTIME / "STRATA_INBOX_QUEUE.json"
GENERATED_QUEUE = RUNTIME / "STRATA_GENERATED_QUEUE.json"
XBOX_QUEUE = ROOT / "XBOX_TASK_QUEUE.json"
OBJECTIVES = ROOT / "STRATA_OBJECTIVES.json"
REVIEW_LOG = ROOT / "STRATA_REVIEWED.json"
LOCK = RUNTIME / ".strata-daemon.lock"
STOP = RUNTIME / "STRATA_STOP"
REJECTIONS = RUNTIME / "STRATA_INBOX_REJECTIONS.json"
ENDURANCE = RUNTIME / "STRATA_ENDURANCE.json"
RECOVERIES = RUNTIME / "STRATA_RECOVERIES.json"
AREA_ROTATION = RUNTIME / "STRATA_AREA_ROTATION.json"
STATUS_BRANCH = "agent/strata-status"
INBOX_BRANCH = "agent/strata-inbox"
APPROVED_AREAS = {*(f"XRE{i:02d}" for i in range(1, 9)), *(f"RE{i:02d}" for i in range(1, 9))}
SENSITIVE = re.compile(r"\b(flash|reboot|voltage change|write register|extract key|bypass signature|install driver)\b", re.I)
STOPPING = False


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def endurance_state():
    if ENDURANCE.exists():
        return load(ENDURANCE)
    state = {"started_utc": utc_now(), "target_seconds": 28800, "work_seconds": 0,
             "idle_seconds": 0, "idle_reason": None, "worker_runs": 0}
    save(ENDURANCE, state)
    return state


def add_duration(field, seconds, reason=None):
    state = endurance_state()
    state[field] = round(state.get(field, 0) + max(0, seconds), 1)
    if reason:
        state["idle_reason"] = reason
    elif field == "work_seconds":
        state["idle_reason"] = None
    save(ENDURANCE, state)


def save(path, value):
    worker.atomic_json(path, value)


def load(path):
    if not path.exists():
        return {"schema_version": 1, "tasks": []}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def gh_api(repo, path, method="GET", payload=None):
    argv = ["gh", "api", f"repos/{repo}/{path}", "-X", method, "-H", "Accept: application/vnd.github+json"]
    if payload is not None:
        argv += ["--input", "-"]
    result = subprocess.run(argv, input=json.dumps(payload) if payload is not None else None,
                            cwd=ROOT, capture_output=True, text=True, timeout=45)
    if result.returncode:
        if "HTTP 404" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip()[:500])
    return json.loads(result.stdout) if result.stdout.strip() else {}


def ensure_branch(repo, branch):
    if gh_api(repo, f"git/ref/heads/{branch}") is not None:
        return
    head = git("rev-parse", "HEAD")
    gh_api(repo, "git/refs", "POST", {"ref": f"refs/heads/{branch}", "sha": head})


def get_content(repo, branch, path):
    result = gh_api(repo, f"contents/{path}?ref={branch}")
    if result is None:
        return None, None
    return base64.b64decode(result["content"]).decode("utf-8"), result["sha"]


def put_content(repo, branch, path, content, message):
    previous, sha = get_content(repo, branch, path)
    if previous == content:
        return False
    payload = {"message": message, "branch": branch,
               "content": base64.b64encode(content.encode("utf-8")).decode("ascii")}
    if sha:
        payload["sha"] = sha
    gh_api(repo, f"contents/{path}", "PUT", payload)
    return True


def task_key(task):
    return hashlib.sha256((task.get("area", "") + "\n" + task["objective"].strip().lower()).encode()).hexdigest()


def validate_incoming(task, branch):
    if not isinstance(task, dict) or not re.fullmatch(r"IN-[A-Za-z0-9-]{3,48}", str(task.get("id", ""))):
        raise ValueError("invalid task ID")
    if task.get("area") not in APPROVED_AREAS:
        raise ValueError("research area is outside the approved set")
    if task.get("branch") != branch or branch not in {"research/xbox-firmware", "research/ps5-firmware"}:
        raise ValueError("task branch does not match the research worktree")
    objective = task.get("objective")
    if not isinstance(objective, str) or not 20 <= len(objective) <= 1000 or SENSITIVE.search(objective):
        raise ValueError("objective is empty, oversized or outside offline research scope")
    paths = task.get("allowed_writes")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 2:
        raise ValueError("one or two output files are required")
    for relative in paths:
        path = worker.confined(relative, writable=True)
        if not (path.relative_to(ROOT).as_posix().startswith("docs/research/") and path.suffix == ".md"):
            raise ValueError("inbox tasks may write only research notes")
    return {"id": task["id"], "area": task["area"], "branch": branch,
            "objective": objective, "allowed_writes": paths, "status": "pending",
            "verify": [["python", "tools/quality/doclint.py", "--files", *paths]],
            "publish": False, "origin": "github_inbox"}


def import_inbox(repo, branch):
    content, _ = get_content(repo, INBOX_BRANCH, "TASK_INBOX.json")
    if content is None:
        put_content(repo, INBOX_BRANCH, "TASK_INBOX.json", '{"schema_version":1,"tasks":[]}\n', "agent: initialize task inbox")
        return 0
    incoming = json.loads(content)
    if incoming.get("schema_version") != 1 or not isinstance(incoming.get("tasks"), list):
        raise ValueError("invalid GitHub task inbox schema")
    inbox = load(INBOX_QUEUE)
    all_tasks = [task for path in (INBOX_QUEUE, XBOX_QUEUE, GENERATED_QUEUE, ROOT / "TASK_QUEUE.json") for task in load(path)["tasks"]]
    ids = {task["id"] for task in all_tasks}
    keys = {task_key(task) for task in all_tasks if "objective" in task}
    rejected = load(REJECTIONS)
    added = 0
    for raw in incoming["tasks"]:
        try:
            task = validate_incoming(raw, branch)
            if task["id"] in ids or task_key(task) in keys:
                continue
            inbox["tasks"].append(task)
            ids.add(task["id"])
            keys.add(task_key(task))
            added += 1
        except (ValueError, KeyError) as error:
            record = {"id": raw.get("id") if isinstance(raw, dict) else None, "reason": str(error)}
            if record not in rejected["tasks"]:
                rejected["tasks"].append(record)
    save(INBOX_QUEUE, inbox)
    save(REJECTIONS, rejected)
    return added


GENERATED = [
    {"id": "AUTO-XRE03-01", "area": "XRE03", "branch": "research/xbox-firmware",
     "objective": "Read XBOX_RESEARCH.md and the pinned XanaduXVD README at https://raw.githubusercontent.com/xboxoneresearch/XanaduXVD/50aa0dc89350de580b77f26ade1018b16b0bc1f8/README.md. Write a short source-derived note on documented XVD container fields and unknown Series X/S applicability. Do not read binaries.",
     "sources": ["XBOX_RESEARCH.md", "https://raw.githubusercontent.com/xboxoneresearch/XanaduXVD/50aa0dc89350de580b77f26ade1018b16b0bc1f8/README.md"],
     "allowed_writes": ["docs/research/xbox-xvd-source-note.md"]},
    {"id": "AUTO-XRE06-01", "area": "XRE06", "branch": "research/xbox-firmware",
     "objective": "Read XBOX_FIRMWARE_INVENTORY.json and tools/firmware/cyan_skillfish2.json. Write a short metadata-only comparison plan for public AMD microcode and unknown Xbox firmware identifiers. Do not read binary firmware.",
     "sources": ["XBOX_FIRMWARE_INVENTORY.json", "tools/firmware/cyan_skillfish2.json"],
     "allowed_writes": ["docs/research/xbox-amd-firmware-metadata-plan.md"]},
]


def generate_task(branch):
    generated = load(GENERATED_QUEUE)
    known = {task["id"] for path in (GENERATED_QUEUE, INBOX_QUEUE, XBOX_QUEUE) for task in load(path)["tasks"]}
    for template in GENERATED:
        if template["branch"] == branch and template["id"] not in known:
            task = dict(template, status="pending", origin="generated", publish=False,
                        verify=[["python", "tools/quality/doclint.py", "--files", *template["allowed_writes"]]])
            generated["tasks"].append(task)
            save(GENERATED_QUEUE, generated)
            return task
    return None


def replenish_backlog(branch, floor=20):
    """Queue only reviewed, source-scoped objectives until the useful backlog floor."""
    if branch != "agent/strata-v2" or not OBJECTIVES.exists():
        return 0
    queue = load(ROOT / "TASK_QUEUE.json")
    templates = json.loads(OBJECTIVES.read_text(encoding="utf-8"))["tasks"]
    other_queues = [INBOX_QUEUE, GENERATED_QUEUE, XBOX_QUEUE]
    known_tasks = queue["tasks"] + [t for path in other_queues for t in load(path)["tasks"]]
    ready = sum(t.get("branch")==branch and t.get("status") in ("pending","retry_scheduled","running") for t in known_tasks)
    known = {t["id"] for t in known_tasks}
    added = 0
    for template in templates:
        if ready >= floor: break
        if template["id"] in known: continue
        if any(not (ROOT / source).is_file() for source in template.get("sources", [])):
            continue
        task = dict(template, branch=branch, status="pending")
        task.setdefault("publish", False)
        task.setdefault("verify", [["python","tools/quality/doclint.py","--files",*task["allowed_writes"]]])
        queue["tasks"].append(task); known.add(task["id"]); ready += 1; added += 1
    if added: save(ROOT / "TASK_QUEUE.json", queue)
    return added


def generate_followup_reviews(branch, floor=5):
    """Review generation is deliberately disabled; reviews are human-gated work."""
    return 0


def next_task(branch):
    now = time.time()
    paths = (INBOX_QUEUE, GENERATED_QUEUE, XBOX_QUEUE, ROOT / "TASK_QUEUE.json")
    candidates = [(path, task) for path in paths for task in load(path)["tasks"]
                  if task.get("branch") == branch and task.get("status") in ("pending", "retry_scheduled", "running")
                  and task.get("retry_at", 0) <= now]
    if not candidates:
        return None, None
    # Recover an existing lease first; otherwise rotate areas so a large queue
    # in one project cannot starve independent work.
    running = next(((path, task) for path, task in candidates if task.get("status") == "running"), None)
    if running:
        return running
    rotation = load(AREA_ROTATION)
    areas = list(dict.fromkeys(task.get("area", "GENERAL") for _, task in candidates))
    last = rotation.get("last_area")
    start = (areas.index(last) + 1) % len(areas) if last in areas else 0
    selected_area = areas[start]
    selected = next(item for item in candidates if item[1].get("area", "GENERAL") == selected_area)
    save(AREA_ROTATION, {"schema_version": 1, "last_area": selected_area, "updated_utc": utc_now()})
    return selected


def update_failure(path, task, stalled=False, reason=None):
    queue = load(path)
    current = next(item for item in queue["tasks"] if item["id"] == task["id"])
    # The worker persists retry/quarantine state itself. Preserve that decision.
    if current.get("status") in ("retry_scheduled", "quarantined"):
        return
    error = current.get("error", reason or ("stalled worker" if stalled else "worker failed before checkpoint"))
    checkpoint = json.loads(worker.CHECKPOINT.read_text(encoding="utf-8")) if worker.CHECKPOINT.exists() else {}
    if checkpoint.get("task") == task["id"]:
        current["output_tokens_total"] = max(int(current.get("output_tokens_total", 0)),
                                              int(checkpoint.get("output_tokens_total", 0)))
        current["input_tokens_total"] = max(int(current.get("input_tokens_total", 0)),
                                             int(checkpoint.get("input_tokens_total", 0)))
        current["tool_call_counts"] = checkpoint.get("tool_call_counts", current.get("tool_call_counts", {}))
    retriable = stalled or any(word in error.lower() for word in ("worker failed before checkpoint", "urlerror", "timed out", "connection", "http 5"))
    attempts = current.get("attempts", 0) + 1
    current["attempts"] = attempts
    if retriable and attempts <= 3:
        current["status"] = "pending"
        current["retry_at"] = time.time() + min(90 * 2 ** (attempts - 1), 300)
    elif "tool round limit" in error.lower() or "context" in error.lower():
        children = current.get("split_tasks", [])
        if not children and len(current.get("sources", [])) > 1 and len(current.get("allowed_writes", [])) == 1:
            output = Path(current["allowed_writes"][0])
            if output.suffix == ".md":
                for index, source in enumerate(current["sources"], 1):
                    part = str(output.with_name(f"{output.stem}-part{index}.md")).replace("\\", "/")
                    children.append({"id": f"{current['id']}-P{index}", "area": current.get("area"),
                                     "objective": f"Inspect only {source}. Record a short source-derived note. Do not read binary firmware or infer boot compatibility.",
                                     "allowed_writes": [part], "sources": [source],
                                     "verify": [["python", "tools/quality/doclint.py", "--files", part]]})
        current["status"] = "split" if children else "blocked"
        for child in children:
            if child["id"] not in {item["id"] for item in queue["tasks"]}:
                queue["tasks"].append(dict(child, branch=current["branch"], status="pending", publish=False, origin="split"))
    else:
        current["status"] = "blocked"
        current["error"] = error[:500]
    save(path, queue)


def task_timeout_reached(started, now, timeout_seconds):
    return now - started >= timeout_seconds


def run_task(path, task, stall_seconds=None, tick=None):
    limits = worker.task_limits(task)
    execution_timeout = limits["max_execution_seconds"]
    progress_timeout = limits["max_progress_stall_seconds"] if stall_seconds is None else stall_seconds
    command = [sys.executable, str(ROOT / "tools/strata_supervisor.py"), "--once", "--queue", str(path), "--task-id", task["id"]]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(command, cwd=ROOT, creationflags=flags,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    start = time.time()
    while process.poll() is None:
        if tick:
            tick(task)
        if STOP.exists() or STOPPING:
            process.terminate()
            process.wait(timeout=10)
            return "stopped"
        elapsed = time.time() - start
        if task_timeout_reached(start, time.time(), execution_timeout):
            process.kill()
            process.wait(timeout=10)
            prior = json.loads(worker.CHECKPOINT.read_text(encoding="utf-8")) if worker.CHECKPOINT.exists() else {}
            output_tokens_total = prior.get("output_tokens_total", task.get("output_tokens_total", 0)) if prior.get("task") == task["id"] else task.get("output_tokens_total", 0)
            input_tokens_total = prior.get("input_tokens_total", task.get("input_tokens_total", 0)) if prior.get("task") == task["id"] else task.get("input_tokens_total", 0)
            tool_call_counts = prior.get("tool_call_counts", task.get("tool_call_counts", {})) if prior.get("task") == task["id"] else task.get("tool_call_counts", {})
            worker.atomic_json(worker.CHECKPOINT, {"task": task["id"], "status": "worker_timeout",
                                                   "elapsed_seconds": round(elapsed, 1),
                                                   "input_tokens_total": input_tokens_total,
                                                   "output_tokens_total": output_tokens_total,
                                                   "tool_call_counts": tool_call_counts})
            update_failure(path, task, stalled=True, reason="TASK_EXECUTION_TIMEOUT")
            return "timed_out"
        checkpoint = worker.CHECKPOINT
        last = checkpoint.stat().st_mtime if checkpoint.exists() else start
        if time.time() - max(last, start) > progress_timeout:
            process.kill()
            process.wait(timeout=10)
            prior = json.loads(worker.CHECKPOINT.read_text(encoding="utf-8")) if worker.CHECKPOINT.exists() else {}
            output_tokens_total = prior.get("output_tokens_total", task.get("output_tokens_total", 0)) if prior.get("task") == task["id"] else task.get("output_tokens_total", 0)
            input_tokens_total = prior.get("input_tokens_total", task.get("input_tokens_total", 0)) if prior.get("task") == task["id"] else task.get("input_tokens_total", 0)
            tool_call_counts = prior.get("tool_call_counts", task.get("tool_call_counts", {})) if prior.get("task") == task["id"] else task.get("tool_call_counts", {})
            worker.atomic_json(worker.CHECKPOINT, {"task": task["id"], "status": "progress_stalled",
                                                   "elapsed_seconds": round(elapsed, 1),
                                                   "input_tokens_total": input_tokens_total,
                                                   "output_tokens_total": output_tokens_total,
                                                   "tool_call_counts": tool_call_counts})
            update_failure(path, task, stalled=True)
            return "stalled"
        time.sleep(5)
    if process.returncode:
        update_failure(path, task)
    return "completed" if process.returncode == 0 else "failed"


def status_payload(branch, state, task):
    tasks_by_id = {}
    for path in (INBOX_QUEUE, XBOX_QUEUE, GENERATED_QUEUE, ROOT / "TASK_QUEUE.json"):
        for item in load(path)["tasks"]:
            tasks_by_id[item["id"]] = item
    tasks = list(tasks_by_id.values())
    metrics = json.loads(worker.METRICS.read_text(encoding="utf-8")) if worker.METRICS.exists() else {}
    endurance = endurance_state()
    now = datetime.now(timezone.utc)
    started = datetime.strptime(endurance["started_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    recoveries = load(RECOVERIES).get("automatic_recoveries", 0)
    reviewed_ids = set(load(REVIEW_LOG).get("reviewed_task_ids", []))
    next_item = next((item["id"] for item in tasks if item.get("branch") == branch and item.get("status") in ("pending", "retry_scheduled") and item.get("retry_at", 0) <= time.time()), None)
    return {"utc": utc_now(), "state": state, "current_task_id": task.get("id") if task else None,
            "research_area": task.get("area") if task else None,
            "completed_count": sum(item.get("branch") == branch and item.get("status") == "done" for item in tasks),
            "failed_count": sum(item.get("branch") == branch and item.get("status") in ("blocked", "quarantined") for item in tasks),
            "tool_calls": metrics.get("tool_calls", 0), "input_tokens": metrics.get("input_tokens"),
            "output_tokens": metrics.get("output_tokens"),
            "last_successful_validation_utc": metrics.get("last_validation_utc"),
            "uptime_seconds": int((now - started).total_seconds()),
            "endurance_target_seconds": endurance["target_seconds"],
            "actual_work_seconds": endurance["work_seconds"],
            "idle_seconds": endurance["idle_seconds"],
            "idle_reason": endurance.get("idle_reason"),
            "automatic_recoveries": recoveries,
            "pending_reviews": sum(item.get("branch") == branch and item.get("status") == "done" and item["id"] not in reviewed_ids for item in tasks),
            "published_commits": int(git("rev-list", "--count", f"--since={endurance['started_utc']}", "HEAD") or 0),
            "last_successful_commit": git("rev-parse", "HEAD"), "next_task_id": next_item,
            "work_branch": branch}


def heartbeat(repo, branch, state, task):
    payload = status_payload(branch, state, task)
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    md = ("# Strata status\n\n" + "\n".join(f"- {key.replace('_', ' ')}: `{value}`" for key, value in payload.items()) + "\n")
    put_content(repo, STATUS_BRANCH, "AGENT_STATUS.json", encoded, "agent: update status JSON")
    put_content(repo, STATUS_BRANCH, "AGENT_STATUS.md", md, "agent: update status summary")
    return payload


def acquire_lock():
    file = LOCK.open("a+b")
    file.write(b"0")
    file.flush()
    file.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return file


def signal_stop(_signum, _frame):
    global STOPPING
    STOPPING = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="gottmoz/amdgpu-wddm")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--heartbeat-seconds", type=int, default=300)
    parser.add_argument("--stall-seconds", type=int)
    parser.add_argument("--once", action="store_true", help="one poll and at most one task")
    parser.add_argument("--bootstrap-only", action="store_true", help="create inbox and publish an idle heartbeat")
    args = parser.parse_args()
    lock = acquire_lock()
    signal.signal(signal.SIGTERM, signal_stop)
    signal.signal(signal.SIGINT, signal_stop)
    branch = git("branch", "--show-current")
    if branch not in ("research/xbox-firmware", "research/ps5-firmware", "agent/strata-v2"):
        raise RuntimeError("run the coordinator in an approved research or agent branch")
    for name in (STATUS_BRANCH, INBOX_BRANCH):
        ensure_branch(args.repo, name)
    if args.bootstrap_only:
        import_inbox(args.repo, branch)
        heartbeat(args.repo, branch, "idle", None)
        lock.close()
        return 0
    last_heartbeat = 0
    endurance_state()
    state = "idle"
    task = None
    try:
        while not (STOP.exists() or STOPPING):
            task = None
            try:
                import_inbox(args.repo, branch)
                generate_task(branch)
                generate_followup_reviews(branch)
                replenish_backlog(branch)
                path, task = next_task(branch)
                state = "working" if task else "idle"
                if time.time() - last_heartbeat >= args.heartbeat_seconds:
                    heartbeat(args.repo, branch, state, task)
                    last_heartbeat = time.time()
                if task:
                    def tick(active):
                        nonlocal last_heartbeat
                        if time.time() - last_heartbeat >= args.heartbeat_seconds:
                            heartbeat(args.repo, branch, "working", active)
                            last_heartbeat = time.time()
                    work_started = time.monotonic()
                    result = run_task(path, task, args.stall_seconds, tick=tick)
                    add_duration("work_seconds", time.monotonic() - work_started)
                    endurance = endurance_state()
                    endurance["worker_runs"] = endurance.get("worker_runs", 0) + 1
                    save(ENDURANCE, endurance)
                    state = "idle"
                    heartbeat(args.repo, branch, state, None)
                    last_heartbeat = time.time()
            except Exception as error:
                state = "error"
                (RUNTIME / "STRATA_DAEMON_ERROR.txt").write_text(f"{utc_now()} {type(error).__name__}: {error}\n", encoding="utf-8")
                try:
                    heartbeat(args.repo, branch, state, task)
                except Exception:
                    pass
            if args.once:
                break
            if task and state != "error":
                continue
            idle_started = time.monotonic()
            for _ in range(max(1, args.poll_seconds)):
                if STOP.exists() or STOPPING:
                    break
                time.sleep(1)
            idle_elapsed = time.monotonic() - idle_started
            add_duration("idle_seconds", idle_elapsed, "no eligible ready task (queue empty or waiting for retry)")
        if not args.once:
            heartbeat(args.repo, branch, "idle", None)
    finally:
        lock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
