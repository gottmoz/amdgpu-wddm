"""Small, restartable task runner for the local Strata OpenAI-compatible API.

Run from the repository root: python tools/strata_supervisor.py [--once]
Only task-declared text files can be published. Never run on main.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import strata_state
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.getenv("BC250_ROOT", str(ROOT.parent))).resolve()
RUNTIME = Path(os.getenv("STRATA_RUNTIME_DIR", str(ROOT))).resolve()
RUNTIME.mkdir(parents=True, exist_ok=True)
QUEUE = ROOT / "TASK_QUEUE.json"
CHECKPOINT = RUNTIME / "STRATA_CHECKPOINT.json"
MEMORY = RUNTIME / "STRATA_MEMORY.jsonl"
METRICS = RUNTIME / "STRATA_METRICS.json"
STATE_DB = RUNTIME / "strata-state.sqlite3"
MODEL_URL = os.getenv("STRATA_URL", "http://127.0.0.1:8080").rstrip("/")
PUBLIC_HOSTS = {"raw.githubusercontent.com", "github.com", "learn.microsoft.com", "www.xbox.com", "news.xbox.com", "www.amd.com", "blog.playstation.com"}
STATS = {"tool_calls": 0, "input_tokens": 0, "output_tokens": 0, "last_validation_utc": None}
if METRICS.exists():
    STATS.update(json.loads(METRICS.read_text(encoding="utf-8")))
TEXT_SUFFIXES = {".md", ".json", ".py", ".ps1", ".yml", ".yaml", ".txt", ".c", ".h"}
FORBIDDEN_PARTS = {".git", "evidence", "secrets", "firmware", "scratch", "toolchain"}
SAFE_COMMANDS = {
    "rg": {"--files", "-n", "-i", "-g", "--glob", "--max-count"},
    "python": {"-m", "-B"},
    "git": {"status", "diff", "log", "show", "branch", "rev-parse"},
}


def atomic_json(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def persist_metrics():
    """Merge counters monotonically so an older worker cannot roll metrics back."""
    latest = {}
    if METRICS.exists():
        try:
            latest = json.loads(METRICS.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            latest = {}
    for key in ("tool_calls", "input_tokens", "output_tokens"):
        STATS[key] = max(int(STATS.get(key, 0)), int(latest.get(key, 0)))
    timestamps = [value for value in (STATS.get("last_validation_utc"), latest.get("last_validation_utc")) if value]
    STATS["last_validation_utc"] = max(timestamps) if timestamps else None
    atomic_json(METRICS, STATS)


def confined(relative, *, writable=False):
    path = (ROOT / relative).resolve()
    repo_relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else ""
    public_manifest = relative == "tools/firmware/cyan_skillfish2.json" and not writable
    public_tool_source = repo_relative.startswith("tools/firmware/") and path.suffix.lower() == ".py"
    if (not path.is_relative_to(ROOT) or (FORBIDDEN_PARTS.intersection(path.relative_to(ROOT).parts)
                                           and not public_manifest and not public_tool_source)
            or path.name.lower().startswith((".env", "credential", "secret"))
            or path.suffix.lower() in {".pem", ".key", ".pfx", ".p12"}):
        raise ValueError("path outside allowed source and documentation tree")
    if writable and (path.suffix.lower() not in TEXT_SUFFIXES or (path.exists() and path.stat().st_size > 1_000_000)):
        raise ValueError("only small text files may be written")
    return path


def run(argv, timeout=120):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout, shell=False)
    return {"exit_code": result.returncode, "stdout": result.stdout[-6000:], "stderr": result.stderr[-3000:]}


def command(args):
    argv = args["argv"]
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise ValueError("argv must be a string list")
    executable = Path(argv[0]).name.lower().removesuffix(".exe")
    if executable not in SAFE_COMMANDS:
        raise ValueError("command is outside the read-only allowlist")
    if executable == "git" and (len(argv) < 2 or argv[1] not in SAFE_COMMANDS["git"]):
        raise ValueError("git mutation is reserved for the supervisor")
    approved_python = argv[1:3] == ["-m", "unittest"] or argv[1:4] == ["-B", "-m", "unittest"] or argv[1:3] == ["-B", "tools/facts/gen_facts.py"]
    if executable == "python" and not approved_python:
        raise ValueError("only approved host tests are allowed")
    if executable == "rg" and any(x.startswith("-") and x not in SAFE_COMMANDS["rg"] for x in argv[1:]):
        raise ValueError("unsupported rg option")
    return run(argv, 90)


def tool(name, args, task):
    sources = task.get("sources")
    if sources:
        if name == "read_file" and args["path"] not in sources:
            raise ValueError("read path is not a declared task source")
        if name == "fetch_url" and args["url"] not in sources:
            raise ValueError("URL is not a declared task source")
        if name not in ("read_file", "fetch_url", "write_file") and not (name == "terminal" and task.get("allow_tests")):
            raise ValueError("source-scoped task permits only source reads and declared writes")
    if name == "list_files":
        if Path(args["glob"]).is_absolute() or ".." in Path(args["glob"]).parts:
            raise ValueError("glob must stay within repository")
        return {"files": [str(p.relative_to(ROOT)).replace("\\", "/") for p in ROOT.glob(args["glob"]) if p.is_file() and not FORBIDDEN_PARTS.intersection(p.relative_to(ROOT).parts)][:80]}
    if name == "read_file":
        return {"content": confined(args["path"]).read_text(encoding="utf-8", errors="replace")[:12000]}
    if name == "fetch_url":
        url = args["url"]
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in PUBLIC_HOSTS or parsed.username or parsed.password:
            raise ValueError("URL is outside approved public source hosts")
        class PublicRedirects(HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, msg, headers, new_url):
                target = urlparse(new_url)
                if target.scheme != "https" or target.hostname not in PUBLIC_HOSTS:
                    raise ValueError("redirect leaves approved public source hosts")
                return super().redirect_request(request, fp, code, msg, headers, new_url)
        request = Request(url, headers={"User-Agent": "BC250-source-review/1.0"})
        with build_opener(PublicRedirects()).open(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if not any(value in content_type for value in ("text/", "application/json")):
                raise ValueError("only public text sources are admitted")
            return {"url": response.url, "content": response.read(12000).decode("utf-8", errors="replace")}
    if name == "write_file":
        if args["path"] not in task["allowed_writes"]:
            raise ValueError("write target is not declared in task")
        path = confined(args["path"], writable=True)
        content = args["content"]
        if len(content.encode("utf-8")) > 100_000:
            raise ValueError("write exceeds task limit")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"written": args["path"], "bytes": len(content.encode("utf-8"))}
    if name in ("terminal", "git"):
        return command(args)
    if name == "compile":
        return run(["pwsh", "-NoProfile", "-File", "driver/kmd/build.ps1", "-Kits", str(WORKSPACE / "toolchain/nuget"), "-Out", str(WORKSPACE / "scratch/strata-kmd"), "-QualityWorkspace", str(WORKSPACE), "-CompileOnly", "-Flavour", "release"], 1800)
    if name == "ghidra_headless":
        ghidra = os.getenv("GHIDRA_HEADLESS")
        if not ghidra or not Path(ghidra).is_file():
            return {"error": "GHIDRA_HEADLESS is not configured"}
        target = (WORKSPACE / args["path"]).resolve()
        if not target.is_relative_to(WORKSPACE) or not target.is_file():
            raise ValueError("analysis input must be an existing workspace file")
        if target.suffix.lower() not in {".bin", ".elf", ".exe", ".dll", ".sys"}:
            raise ValueError("unsupported static analysis input")
        project = WORKSPACE / "scratch/ghidra"
        project.mkdir(parents=True, exist_ok=True)
        return run([ghidra, str(project), "strata", "-import", str(target), "-deleteProject"], 1200)
    raise ValueError("unknown tool")


def definitions(task):
    def spec(name, description, properties, required):
        return {"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required}}}
    string = {"type": "string"}
    argv = {"type": "array", "items": string}
    all_tools = [
        spec("list_files", "List up to 80 matching repository paths", {"glob": string}, ["glob"]),
        spec("read_file", "Read at most 12k characters", {"path": string}, ["path"]),
        spec("fetch_url", "Read at most 12k bytes of an approved public source", {"url": string}, ["url"]),
        spec("write_file", "Write only a task-declared text file", {"path": string, "content": string}, ["path", "content"]),
        spec("terminal", "Read-only search or approved host test", {"argv": argv}, ["argv"]),
        spec("git", "Read-only Git inspection", {"argv": argv}, ["argv"]),
        spec("compile", "Build KMD CompileOnly without installation", {}, []),
        spec("ghidra_headless", "Static analysis when GHIDRA_HEADLESS is configured", {"path": string}, ["path"]),
    ]
    allowed=set(task.get("tools", []))
    if task.get("sources"):
        allowed.update(("read_file", "write_file"))
        if task.get("allow_public_fetch"): allowed.add("fetch_url")
        if task.get("allow_tests"): allowed.add("terminal")
    if not allowed: allowed.update(("read_file", "list_files", "write_file"))
    return [item for item in all_tools if item["function"]["name"] in allowed]


def api(messages, model, task):
    tools=definitions(task)
    body = json.dumps({"model": model, "messages": messages, "tools": tools, "tool_choice": "auto", "max_tokens": 2000, "temperature": 0}).encode()
    headers = {"Content-Type": "application/json"}
    if os.getenv("STRATA_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["STRATA_API_KEY"]
    request = Request(MODEL_URL + "/v1/chat/completions", data=body, headers=headers)
    with urlopen(request, timeout=float(os.getenv("STRATA_API_TIMEOUT", "240"))) as response:
        payload = json.load(response)
    usage = payload.get("usage") or {}
    STATS["input_tokens"] += usage.get("prompt_tokens", 0)
    STATS["output_tokens"] += usage.get("completion_tokens", 0)
    try:
        choice=payload["choices"][0]
        if not isinstance(choice.get("message"),dict): raise ValueError("missing message")
        return choice
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError(f"MALFORMED_MODEL_RESPONSE: {exc}") from exc


def active_model():
    with urlopen(MODEL_URL + "/v1/models", timeout=10) as response:
        models = json.load(response)["data"]
    return models[0]["id"]


def current_branch():
    return run(["git", "branch", "--show-current"])["stdout"].strip()


def publish(task):
    if task.get("publication_policy") != "unit-tested-code":
        raise RuntimeError("automatic publication requires unit-tested-code policy")
    allowed_prefixes = ("tools/firmware/", "tools/tests/", "tools/release/")
    declared = task.get("allowed_writes", [])
    if not declared or any(not path.replace("\\", "/").startswith(allowed_prefixes)
                           or Path(path).suffix.lower() not in {".py", ".json"} for path in declared):
        raise RuntimeError("automatic publication is limited to declared Python tools/tests and JSON metadata")
    checks = task.get("verify", [])
    if not any(isinstance(check, list) and len(check) >= 3 and check[:2] == ["python", "-m"]
               and check[2] == "unittest" for check in checks):
        raise RuntimeError("automatic publication requires a declared unittest validation")
    branch = current_branch()
    if branch != task["branch"] or branch == "main":
        raise RuntimeError("publication branch mismatch or main")
    if run(["git", "diff", "--cached", "--quiet"])["exit_code"] != 0:
        raise RuntimeError("publication requires an empty Git index")
    paths = list(declared)
    for relative in paths:
        tracked = run(["git", "ls-files", "--error-unmatch", "--", relative])
        if tracked["exit_code"] == 0:
            change = run(["git", "diff", "--numstat", "--", relative])
            if change["stdout"].strip():
                fields = change["stdout"].splitlines()[0].split("\t")
                if len(fields) != 3 or not fields[0].isdigit() or not fields[1].isdigit():
                    raise RuntimeError("could not validate changed-line counts")
                added, deleted = int(fields[0]), int(fields[1])
                if deleted > 20 or deleted > added:
                    raise RuntimeError("automatic publication rejects large deletion from an existing file")
        path = confined(relative)
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 100_000:
            raise RuntimeError("publication requires small declared text files")
        content = path.read_text(encoding="utf-8")
        if re.search(r"-----BEGIN .*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}", content):
            raise RuntimeError("possible credential in publication")
    review_log = ROOT / "STRATA_REVIEWED.json"
    review_data = json.loads(review_log.read_text(encoding="utf-8")) if review_log.exists() else {"schema_version": 1, "reviewed_task_ids": []}
    if task["id"] not in review_data["reviewed_task_ids"]:
        review_data["reviewed_task_ids"].append(task["id"])
    review_data["reviewed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    review_data["review_basis"] = "Automatically published after declared deterministic unittest validation and restricted-path/credential checks."
    atomic_json(review_log, review_data)
    paths.append("STRATA_REVIEWED.json")
    for argv in (["git", "add", "--", *paths], ["git", "commit", "-m", task["commit_message"]], ["git", "push", "origin", branch]):
        result = run(argv, 120)
        if result["exit_code"]:
            raise RuntimeError(result["stderr"] or result["stdout"])
    return run(["git", "rev-parse", "HEAD"])["stdout"].strip()


def work(task, model):
    memory = MEMORY.read_text(encoding="utf-8").splitlines()[-8:] if MEMORY.exists() else []
    fixed_sources = task.get("sources", [])
    available_tools = [item["function"]["name"] for item in definitions(task)]
    examples = {}
    if "read_file" in available_tools:
        examples["read_file"] = {"path": fixed_sources[0] if fixed_sources else "README.md"}
    if "list_files" in available_tools:
        examples["list_files"] = {"glob": task.get("list_glob", "docs/research/ps5-dump-strata-review.md")}
    if "write_file" in available_tools:
        examples["write_file"] = {"path": task["allowed_writes"][0] if task.get("allowed_writes") else "", "content": "..."}
    if "terminal" in available_tools:
        examples["terminal"] = {"argv": task.get("test_command", ["python", "-m", "unittest", "tools.test_strata_daemon"])}
    base = [
        {"role": "system", "content": "You are a local BC-250 engineering agent. Use only the exposed task-scoped tools. File access is not implicit: read_file may read only exact paths in sources, and write_file may write only exact paths in allowed_writes. Never read user-profile, Strata application, environment, secret or undeclared paths. Do not touch hardware or firmware bytes. For terminal, run only the supplied test_command. If a source is insufficient, continue with a bounded implementation from the declared source and document the limitation in the output. Complete the declared artifact and keep the final summary concise."},
        {"role": "user", "content": json.dumps({"objective": task["objective"], "sources": fixed_sources, "allowed_writes": task["allowed_writes"], "available_tools": available_tools, "tool_limits": {"read_file": "exact paths listed in sources only", "write_file": "exact paths listed in allowed_writes only", "terminal": "only test_command"}, "examples": examples, "test_command": task.get("test_command"), "previous_validation_error": task.get("validation_error"), "prior_tool_errors": task.get("invalid_tool_history", []), "prior_memory": memory}, ensure_ascii=False)},
    ]
    recent = []
    compact = []
    for step in range(100):
        summary = [{"role": "user", "content": "Earlier tool actions, compacted:\n" + "\n".join(compact[-20:])}] if compact else []
        messages = base + summary + [message for group in recent for message in group]
        choice = api(messages, model, task)
        message = choice["message"]
        group = [{k: v for k, v in message.items() if k in ("role", "content", "tool_calls")}]
        calls = message.get("tool_calls") or []
        if not calls:
            if all(confined(path).is_file() for path in task["allowed_writes"]):
                atomic_json(CHECKPOINT, {"task": task["id"], "step": step, "status": "response", "summary": (message.get("content") or "")[:3000]})
                return message.get("content") or ""
            group.append({"role": "user", "content": "Write the declared output file using write_file now. Keep it short."})
        else:
            for call in calls:
                STATS["tool_calls"] += 1
                args = {}
                try:
                    args = json.loads(call["function"]["arguments"])
                    name=call["function"]["name"]
                    if name not in {x["function"]["name"] for x in definitions(task)}:
                        raise PermissionError(f"TOOL_NOT_ALLOWED: {name}")
                    result = tool(name, args, task)
                except Exception as error:
                    code="TOOL_NOT_ALLOWED" if isinstance(error,PermissionError) else "INVALID_TOOL_CALL"
                    history = task.setdefault("invalid_tool_history", [])
                    history.append({"tool": call.get("function", {}).get("name", "unknown"),
                                    "argument_keys": sorted(args) if isinstance(args, dict) else [],
                                    "path": args.get("path") if isinstance(args, dict) else None,
                                    "reason": str(error)[:300]})
                    del history[:-3]
                    result = {"error_code":code,"reason":str(error),"available_tools":[x["function"]["name"] for x in definitions(task)],"suggested_action":f"Do not retry that path. Read only one of these exact declared sources: {fixed_sources}. Write only to: {task['allowed_writes']}. For terminal, use the supplied test_command: {task.get('test_command')}"}
                    invalid=int(task.get("invalid_tool_calls",0))+1; task["invalid_tool_calls"]=invalid
                    if invalid>=3:
                        atomic_json(CHECKPOINT,{"task":task["id"],"status":"retry_scheduled","reason":code,"invalid_calls":invalid,"last_error":history[-1]})
                        raise RuntimeError("RETRY_SCHEDULED: repeated invalid tool calls")
                group.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, ensure_ascii=False)[:7000]})
                atomic_json(CHECKPOINT, {"task": task["id"], "step": step, "status": "tool", "tool": call["function"]["name"], "result": str(result)[:1000]})
                db = strata_state.connect(STATE_DB)
                try: strata_state.checkpoint(db, task["id"], {"step": step, "tool": call["function"]["name"], "result": str(result)[:1000]})
                finally: db.close()
                persist_metrics()
        recent.append(group)
        if len(recent) > 6:
            old = recent.pop(0)
            for item in old:
                for call in item.get("tool_calls", []):
                    compact.append(f"step {step}: {call['function']['name']} {call['function']['arguments'][:120]}")
            compact = compact[-20:]
    raise RuntimeError("tool round limit reached; split the task")


def main():
    global QUEUE
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--queue", type=Path, default=QUEUE)
    parser.add_argument("--task-id")
    args = parser.parse_args()
    QUEUE = args.queue if args.queue.is_absolute() else ROOT / args.queue
    model = active_model()
    state_db = strata_state.connect(STATE_DB)
    strata_state.recover_running(state_db)
    while True:
        queue = json.loads(QUEUE.read_text(encoding="utf-8"))
        task = next((item for item in queue["tasks"] if (item["status"] in ("pending", "retry_scheduled") or (args.task_id and item["id"] == args.task_id and item["status"] == "running")) and item.get("retry_at",0)<=time.time() and (not args.task_id or item["id"] == args.task_id)), None)
        if task is None:
            return 0
        if current_branch() != task["branch"] or task["branch"] == "main":
            raise RuntimeError("switch to the task branch before running")
        task["status"] = "running"
        atomic_json(QUEUE, queue)
        strata_state.upsert_task(state_db, task, "running")
        try:
            summary = work(task, model)
            if not all(confined(path).is_file() for path in task["allowed_writes"]):
                raise RuntimeError("task returned without writing declared output")
            for check in task.get("verify", []):
                result = run(check, 180)
                if result["exit_code"]:
                    detail=result["stdout"][-1500:]+result["stderr"][-1500:]
                    task["validation_error"]=detail
                    raise RuntimeError("validation failed. Correct the declared output and retry. " + detail)
            if task.get("verify"):
                STATS["last_validation_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                with state_db: state_db.execute("INSERT INTO validations(task_id,result,created_utc) VALUES(?,?,?)",(task["id"],"passed",STATS["last_validation_utc"]))
            task.update(status="done", summary=summary[:1000])
            atomic_json(QUEUE, queue)
            commit = publish(task) if task.get("publish") else None
            if commit:
                task["commit"] = commit
        except Exception as error:
            attempts=int(task.get("attempts",0))+1
            task.update(status="retry_scheduled" if attempts<=3 else "quarantined",attempts=attempts,error=str(error)[:1000],retry_at=time.time()+min(60*2**(attempts-1),900))
        finally:
            try:
                atomic_json(QUEUE, queue)
                strata_state.upsert_task(state_db, task, task["status"])
                with MEMORY.open("a", encoding="utf-8") as file:
                    file.write(json.dumps({"id": task["id"], "status": task["status"], "summary": task.get("summary"), "error": task.get("error"), "commit": task.get("commit")}, ensure_ascii=False) + "\n")
                atomic_json(CHECKPOINT, {"task": task["id"], "status": task["status"], "attempts": task.get("attempts",0)})
                persist_metrics()
            except Exception as persist_error:
                strata_state.event(state_db,"persistence_error",{"task":task.get("id"),"error":str(persist_error)})
        if args.once: state_db.close(); return 0 if task["status"]=="done" else 1
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
