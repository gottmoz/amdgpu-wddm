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


def confined(relative, *, writable=False):
    path = (ROOT / relative).resolve()
    if (not path.is_relative_to(ROOT) or FORBIDDEN_PARTS.intersection(path.relative_to(ROOT).parts)
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
    if executable == "python" and (len(argv) < 3 or argv[1:3] not in (["-m", "unittest"], ["-B", "tools/facts/gen_facts.py"])):
        raise ValueError("only approved host tests are allowed")
    if executable == "rg" and any(x.startswith("-") and x not in SAFE_COMMANDS["rg"] for x in argv[1:]):
        raise ValueError("unsupported rg option")
    return run(argv, 90)


def tool(name, args, task):
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


def definitions():
    def spec(name, description, properties, required):
        return {"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required}}}
    string = {"type": "string"}
    argv = {"type": "array", "items": string}
    return [
        spec("list_files", "List up to 80 matching repository paths", {"glob": string}, ["glob"]),
        spec("read_file", "Read at most 12k characters", {"path": string}, ["path"]),
        spec("fetch_url", "Read at most 12k bytes of an approved public source", {"url": string}, ["url"]),
        spec("write_file", "Write only a task-declared text file", {"path": string, "content": string}, ["path", "content"]),
        spec("terminal", "Read-only search or approved host test", {"argv": argv}, ["argv"]),
        spec("git", "Read-only Git inspection", {"argv": argv}, ["argv"]),
        spec("compile", "Build KMD CompileOnly without installation", {}, []),
        spec("ghidra_headless", "Static analysis when GHIDRA_HEADLESS is configured", {"path": string}, ["path"]),
    ]


def api(messages, model):
    body = json.dumps({"model": model, "messages": messages, "tools": definitions(), "tool_choice": "auto", "max_tokens": 2000, "temperature": 0}).encode()
    headers = {"Content-Type": "application/json"}
    if os.getenv("STRATA_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["STRATA_API_KEY"]
    request = Request(MODEL_URL + "/v1/chat/completions", data=body, headers=headers)
    with urlopen(request, timeout=180) as response:
        payload = json.load(response)
    usage = payload.get("usage") or {}
    STATS["input_tokens"] += usage.get("prompt_tokens", 0)
    STATS["output_tokens"] += usage.get("completion_tokens", 0)
    return payload["choices"][0]


def active_model():
    with urlopen(MODEL_URL + "/v1/models", timeout=10) as response:
        models = json.load(response)["data"]
    return models[0]["id"]


def current_branch():
    return run(["git", "branch", "--show-current"])["stdout"].strip()


def publish(task):
    branch = current_branch()
    if branch != task["branch"] or branch == "main":
        raise RuntimeError("publication branch mismatch or main")
    if run(["git", "diff", "--cached", "--quiet"])["exit_code"] != 0:
        raise RuntimeError("publication requires an empty Git index")
    paths = [*task["allowed_writes"], "TASK_QUEUE.json"]
    for relative in paths:
        path = confined(relative)
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 100_000:
            raise RuntimeError("publication requires small declared text files")
        content = path.read_text(encoding="utf-8")
        if re.search(r"-----BEGIN .*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}", content):
            raise RuntimeError("possible credential in publication")
    for argv in (["git", "add", "--", *paths], ["git", "commit", "-m", task["commit_message"]], ["git", "push", "origin", branch]):
        result = run(argv, 120)
        if result["exit_code"]:
            raise RuntimeError(result["stderr"] or result["stdout"])
    return run(["git", "rev-parse", "HEAD"])["stdout"].strip()


def work(task, model):
    memory = MEMORY.read_text(encoding="utf-8").splitlines()[-8:] if MEMORY.exists() else []
    base = [
        {"role": "system", "content": "You are a local BC-250 research and development agent. Work on exactly one small task. Inspect evidence and cite repository paths. Distinguish verified observations from hypotheses. Do not touch hardware, secrets, or firmware bytes. Use tools when needed. Keep output concise."},
        {"role": "user", "content": json.dumps({"objective": task["objective"], "allowed_writes": task["allowed_writes"], "prior_memory": memory}, ensure_ascii=False)},
    ]
    recent = []
    compact = []
    for step in range(100):
        summary = [{"role": "user", "content": "Earlier tool actions, compacted:\n" + "\n".join(compact[-20:])}] if compact else []
        messages = base + summary + [message for group in recent for message in group]
        choice = api(messages, model)
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
                try:
                    args = json.loads(call["function"]["arguments"])
                    result = tool(call["function"]["name"], args, task)
                except Exception as error:
                    result = {"error": str(error)}
                group.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, ensure_ascii=False)[:7000]})
                atomic_json(CHECKPOINT, {"task": task["id"], "step": step, "status": "tool", "tool": call["function"]["name"], "result": str(result)[:1000]})
                atomic_json(METRICS, STATS)
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
    while True:
        queue = json.loads(QUEUE.read_text(encoding="utf-8"))
        task = next((item for item in queue["tasks"] if item["status"] in ("pending", "running") and (not args.task_id or item["id"] == args.task_id)), None)
        if task is None:
            return 0
        if current_branch() != task["branch"] or task["branch"] == "main":
            raise RuntimeError("switch to the task branch before running")
        task["status"] = "running"
        atomic_json(QUEUE, queue)
        try:
            summary = work(task, model)
            if not all(confined(path).is_file() for path in task["allowed_writes"]):
                raise RuntimeError("task returned without writing declared output")
            for check in task.get("verify", []):
                result = run(check, 180)
                if result["exit_code"]:
                    raise RuntimeError("verification failed: " + str(check) + " " + result["stderr"][-1000:])
            if task.get("verify"):
                STATS["last_validation_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            task.update(status="done", summary=summary[:1000])
            atomic_json(QUEUE, queue)
            commit = publish(task) if task.get("publish") else None
            if commit:
                task["commit"] = commit
        except Exception as error:
            task.update(status="blocked", error=str(error)[:1000])
        atomic_json(QUEUE, queue)
        with MEMORY.open("a", encoding="utf-8") as file:
            file.write(json.dumps({"id": task["id"], "status": task["status"], "summary": task.get("summary"), "error": task.get("error"), "commit": task.get("commit")}, ensure_ascii=False) + "\n")
        atomic_json(CHECKPOINT, {"task": task["id"], "status": task["status"]})
        atomic_json(METRICS, STATS)
        if args.once or task["status"] == "blocked":
            return 0 if task["status"] == "done" else 1
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
