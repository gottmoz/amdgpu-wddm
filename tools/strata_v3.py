"""Profile-validated entry point for isolated Strata V3 workers."""

from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path
import subprocess
import sys

try:
    from .strata_worker_profile import activate_profile, load_profile
except ImportError:  # Direct script execution places tools/ on sys.path.
    from strata_worker_profile import activate_profile, load_profile


ROOT = Path(__file__).resolve().parents[1]
DAEMON = ROOT / "tools" / "strata_daemon.py"


def prepare_worker(profile_path, *, current_root=ROOT, current_branch=None):
    root = Path(current_root).resolve()
    if current_branch is None:
        try:
            data = json.loads(Path(profile_path).read_text(encoding="utf-8"))
            worktree = Path(data["worktree"]).resolve()
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise ValueError(f"worker profile cannot identify its worktree: {error}") from error
        result = subprocess.run(["git", "branch", "--show-current"], cwd=worktree,
                                capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise ValueError("could not verify the current Git branch")
        current_branch = result.stdout.strip()
    profile = load_profile(profile_path, repo_root=root, current_branch=current_branch)
    activate_profile(profile)
    return profile


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--repo", default="gottmoz/amdgpu-wddm")
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--heartbeat-seconds", type=int, default=60)
    parser.add_argument("--stall-seconds", type=int)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--bootstrap-only", action="store_true")
    args = parser.parse_args(argv)
    prepare_worker(args.profile)

    forwarded = ["--repo", args.repo, "--poll-seconds", str(args.poll_seconds),
                 "--heartbeat-seconds", str(args.heartbeat_seconds)]
    if args.stall_seconds is not None:
        forwarded.extend(("--stall-seconds", str(args.stall_seconds)))
    if args.once:
        forwarded.append("--once")
    if args.bootstrap_only:
        forwarded.append("--bootstrap-only")
    sys.argv = [str(DAEMON), *forwarded]
    runpy.run_path(str(DAEMON), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
