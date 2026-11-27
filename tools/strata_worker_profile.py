"""Validate and activate an isolated Strata worker profile."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess


PROFILE_BRANCHES = {
    "ps5": "research/ps5-firmware",
    "xbox": "research/xbox-firmware",
    "nagi": "agent/strata-nagi",
    "coordinator": "agent/strata-v3",
}
PROFILE_STATUSES = {
    "ps5": "STRATA_PS5_STATUS.json",
    "xbox": "STRATA_XBOX_STATUS.json",
    "nagi": "STRATA_NAGI_STATUS.json",
    "coordinator": "STRATA_V3_STATUS.json",
}
PROFILE_TYPES = {
    "ps5": {"PS5"},
    "xbox": {"XBOX"},
    "nagi": {"NAGI"},
    "coordinator": {"COORDINATOR"},
}
PROFILE_AREAS = {
    "ps5": {f"RE{i:02d}" for i in range(1, 9)},
    "xbox": {f"XRE{i:02d}" for i in range(1, 9)},
    "nagi": {"NAGI"},
    "coordinator": set(),
}
PATH_KEYS = {
    "queue", "inbox_queue", "generated_queue", "xbox_queue", "checkpoint",
    "memory", "sqlite", "metrics", "log_dir", "review_log", "endurance",
    "recoveries", "area_rotation", "rejections", "stop", "lock", "worker_pid", "watchdog_pid",
}
LIMITS = {
    "max_response_tokens": ("STRATA_MAX_RESPONSE_TOKENS", 8192, 16384),
    "max_output_tokens": ("STRATA_MAX_TASK_OUTPUT_TOKENS", 20000, 40000),
    "max_execution_seconds": ("STRATA_TASK_TIMEOUT_SECONDS", 900, 7200),
    "max_progress_stall_seconds": ("STRATA_PROGRESS_TIMEOUT_SECONDS", 900, 7200),
    "max_identical_tool_calls": ("STRATA_MAX_IDENTICAL_TOOL_CALLS", 2, 3),
    "max_history_groups": ("STRATA_MAX_HISTORY_GROUPS", 3, 8),
}


@dataclass(frozen=True)
class WorkerProfile:
    worker_id: str
    worktree: Path
    approved_branch: str
    runtime_root: Path
    runtime_dir: Path
    paths: dict[str, Path]
    status_branch: str
    status_file: str
    allowed_task_types: tuple[str, ...]
    allowed_areas: tuple[str, ...]
    limits: dict[str, int]

    def environment(self) -> dict[str, str]:
        env = {
            "STRATA_WORKER_ID": self.worker_id,
            "STRATA_WORKER_BRANCH": self.approved_branch,
            "STRATA_STATUS_BRANCH": self.status_branch,
            "STRATA_STATUS_FILE": self.status_file,
            "STRATA_STATUS_MD_FILE": "",
            "STRATA_ALLOWED_TASK_TYPES": json.dumps(self.allowed_task_types),
            "STRATA_ALLOWED_AREAS": json.dumps(self.allowed_areas),
            "STRATA_RUNTIME_DIR": str(self.runtime_dir),
            "STRATA_WORKTREE_ROOT": str(self.worktree),
            "STRATA_QUEUE_PATH": str(self.paths["queue"]),
            "STRATA_INBOX_QUEUE_PATH": str(self.paths["inbox_queue"]),
            "STRATA_GENERATED_QUEUE_PATH": str(self.paths["generated_queue"]),
            "STRATA_XBOX_QUEUE_PATH": str(self.paths["xbox_queue"]),
            "STRATA_CHECKPOINT_PATH": str(self.paths["checkpoint"]),
            "STRATA_MEMORY_PATH": str(self.paths["memory"]),
            "STRATA_SQLITE_PATH": str(self.paths["sqlite"]),
            "STRATA_METRICS_PATH": str(self.paths["metrics"]),
            "STRATA_LOG_DIR": str(self.paths["log_dir"]),
            "STRATA_REVIEW_LOG_PATH": str(self.paths["review_log"]),
            "STRATA_ENDURANCE_PATH": str(self.paths["endurance"]),
            "STRATA_RECOVERIES_PATH": str(self.paths["recoveries"]),
            "STRATA_AREA_ROTATION_PATH": str(self.paths["area_rotation"]),
            "STRATA_REJECTIONS_PATH": str(self.paths["rejections"]),
            "STRATA_STOP_PATH": str(self.paths["stop"]),
            "STRATA_LOCK_PATH": str(self.paths["lock"]),
            "STRATA_WORKER_PID_PATH": str(self.paths["worker_pid"]),
            "STRATA_WATCHDOG_PID_PATH": str(self.paths["watchdog_pid"]),
        }
        for name, value in self.limits.items():
            env[LIMITS[name][0]] = str(value)
        return env


def git_common_dir(path: str | Path) -> Path:
    result = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=path,
                            capture_output=True, text=True, timeout=15)
    if result.returncode or not result.stdout.strip():
        raise ValueError("worker and supervisor paths must be Git worktrees")
    common = Path(result.stdout.strip())
    return (Path(path) / common).resolve() if not common.is_absolute() else common.resolve()


def load_profile(path: str | Path, *, repo_root: str | Path,
                 current_branch: str) -> WorkerProfile:
    profile_path = Path(path).resolve()
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"worker profile cannot be read: {error}") from error
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("unsupported worker profile schema")

    worker_id = data.get("worker_id")
    if worker_id not in PROFILE_BRANCHES:
        raise ValueError("worker ID is not approved")
    worktree = Path(data.get("worktree", "")).resolve()
    root = Path(repo_root).resolve()
    if worktree != root and git_common_dir(worktree) != git_common_dir(root):
        raise ValueError("worker worktree must belong to the same Git repository as the supervisor")
    branch = data.get("approved_branch")
    if branch != PROFILE_BRANCHES[worker_id]:
        raise ValueError("approved branch is not approved for this worker ID")
    if current_branch != branch or current_branch == "main":
        raise ValueError("current Git branch does not match the approved branch")

    runtime_root = Path(data.get("runtime_root", "")).resolve()
    runtime_dir = Path(data.get("runtime_dir", "")).resolve()
    if runtime_dir != (runtime_root / worker_id).resolve():
        raise ValueError("runtime directory must be worker-specific")
    if runtime_root == root or runtime_root.is_relative_to(root):
        raise ValueError("runtime root must stay outside the worktree")

    raw_paths = data.get("paths")
    if not isinstance(raw_paths, dict) or set(raw_paths) != PATH_KEYS:
        raise ValueError("worker paths must define the complete isolated state set")
    paths = {}
    for key, value in raw_paths.items():
        if not isinstance(value, str) or not value or Path(value).is_absolute():
            raise ValueError(f"worker path {key!r} must be relative to its runtime directory")
        resolved = (runtime_dir / value).resolve()
        if not resolved.is_relative_to(runtime_dir):
            raise ValueError(f"worker path {key!r} is outside worker runtime")
        paths[key] = resolved

    status_branch = data.get("status_branch")
    status_file = data.get("status_file")
    if status_branch != "agent/strata-status" or status_file != PROFILE_STATUSES[worker_id]:
        raise ValueError("status branch or status file is not approved for this worker")
    if status_file == "AGENT_STATUS.json":
        raise ValueError("workers may not write the shared AGENT_STATUS.json file")

    task_types = data.get("allowed_task_types")
    areas = data.get("allowed_areas")
    if (not isinstance(task_types, list) or not task_types
            or len(set(task_types)) != len(task_types)
            or not set(task_types).issubset(PROFILE_TYPES[worker_id])):
        raise ValueError("task type is outside this worker's approved scope")
    if (not isinstance(areas, list) or len(set(areas)) != len(areas)
            or not set(areas).issubset(PROFILE_AREAS[worker_id])):
        raise ValueError("task area is outside this worker's approved scope")

    raw_limits = data.get("limits")
    if not isinstance(raw_limits, dict) or set(raw_limits) != set(LIMITS):
        raise ValueError("worker execution limits are incomplete")
    limits = {}
    for name, value in raw_limits.items():
        low, high = LIMITS[name][1:]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"execution limit {name!r} is outside approved bounds")
        limits[name] = value
    if limits["max_response_tokens"] > limits["max_output_tokens"]:
        raise ValueError("response token limit exceeds task output limit")

    return WorkerProfile(
        worker_id=worker_id,
        worktree=worktree,
        approved_branch=branch,
        runtime_root=runtime_root,
        runtime_dir=runtime_dir,
        paths=paths,
        status_branch=status_branch,
        status_file=status_file,
        allowed_task_types=tuple(task_types),
        allowed_areas=tuple(areas),
        limits=limits,
    )


def activate_profile(profile: WorkerProfile) -> None:
    profile.runtime_dir.mkdir(parents=True, exist_ok=True)
    profile.paths["log_dir"].mkdir(parents=True, exist_ok=True)
    os.environ.update(profile.environment())
