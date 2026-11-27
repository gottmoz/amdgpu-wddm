import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.strata_worker_profile import WorkerProfile, load_profile
from tools.strata_v3 import prepare_worker


class WorkerProfileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo = base / "repo"
        self.runtime_root = base / "runtime"
        self.runtime = self.runtime_root / "ps5"
        self.profile_path = base / "ps5.json"
        self.profile = {
            "schema_version": 1,
            "worker_id": "ps5",
            "worktree": str(self.repo),
            "approved_branch": "research/ps5-firmware",
            "runtime_root": str(self.runtime_root),
            "runtime_dir": str(self.runtime),
            "paths": {
                "queue": "queue.json",
                "inbox_queue": "inbox.json",
                "generated_queue": "generated.json",
                "xbox_queue": "xbox.json",
                "checkpoint": "checkpoint.json",
                "memory": "memory.jsonl",
                "sqlite": "state.sqlite3",
                "metrics": "metrics.json",
                "log_dir": "logs",
                "review_log": "reviewed.json",
                "endurance": "endurance.json",
                "recoveries": "recoveries.json",
                "area_rotation": "area-rotation.json",
                "rejections": "rejections.json",
                "stop": "STOP",
                "lock": "daemon.lock",
                "worker_pid": "worker.pid",
                "watchdog_pid": "watchdog.pid",
            },
            "status_branch": "agent/strata-status",
            "status_file": "STRATA_PS5_STATUS.json",
            "allowed_task_types": ["PS5"],
            "allowed_areas": ["RE01", "RE02", "RE03", "RE04", "RE05", "RE06", "RE07", "RE08"],
            "limits": {
                "max_response_tokens": 8192,
                "max_output_tokens": 20000,
                "max_execution_seconds": 900,
                "max_progress_stall_seconds": 900,
                "max_identical_tool_calls": 2,
                "max_history_groups": 3,
            },
        }
        self.write_profile()

    def write_profile(self):
        self.profile_path.write_text(json.dumps(self.profile), encoding="utf-8")

    def load(self, branch="research/ps5-firmware"):
        return load_profile(self.profile_path, repo_root=self.repo, current_branch=branch)

    def test_profile_resolves_worker_owned_runtime_files(self):
        profile = self.load()

        self.assertIsInstance(profile, WorkerProfile)
        self.assertEqual(profile.worker_id, "ps5")
        self.assertEqual(profile.paths["queue"], self.runtime / "queue.json")
        self.assertEqual(profile.paths["worker_pid"], self.runtime / "worker.pid")
        self.assertEqual(profile.paths["watchdog_pid"], self.runtime / "watchdog.pid")
        self.assertEqual(profile.status_file, "STRATA_PS5_STATUS.json")

    def test_profile_requires_exact_worktree_and_branch(self):
        with self.assertRaisesRegex(ValueError, "approved branch"):
            self.load("agent/strata-v2")

        self.profile["approved_branch"] = "main"
        self.write_profile()
        with self.assertRaisesRegex(ValueError, "not approved"):
            self.load("main")

    def test_profile_rejects_runtime_path_outside_its_worker_directory(self):
        self.profile["paths"]["checkpoint"] = str(self.runtime_root / "xbox" / "checkpoint.json")
        self.write_profile()

        with self.assertRaisesRegex(ValueError, "relative to its runtime directory"):
            self.load()

    def test_profile_rejects_another_workers_runtime_directory(self):
        self.profile["runtime_dir"] = str(self.runtime_root / "xbox")
        self.write_profile()

        with self.assertRaisesRegex(ValueError, "worker-specific"):
            self.load()

    def test_profile_rejects_shared_status_file(self):
        self.profile["status_file"] = "AGENT_STATUS.json"
        self.write_profile()

        with self.assertRaisesRegex(ValueError, "status file"):
            self.load()

    def test_profile_rejects_task_type_outside_worker_scope(self):
        self.profile["allowed_task_types"] = ["PS5", "NAGI"]
        self.write_profile()

        with self.assertRaisesRegex(ValueError, "task type"):
            self.load()

    def test_profile_rejects_unapproved_task_areas(self):
        self.profile["allowed_areas"] = ["NAGI", "RE01"]
        self.write_profile()

        with self.assertRaisesRegex(ValueError, "task area"):
            self.load()

    def test_profile_rejects_oversized_execution_budget(self):
        self.profile["limits"]["max_execution_seconds"] = 86400
        self.write_profile()

        with self.assertRaisesRegex(ValueError, "execution limit"):
            self.load()

    def test_profile_exports_isolated_paths_and_limits(self):
        profile = self.load()
        environment = profile.environment()

        self.assertEqual(environment["STRATA_RUNTIME_DIR"], str(self.runtime))
        self.assertEqual(environment["STRATA_QUEUE_PATH"], str(self.runtime / "queue.json"))
        self.assertEqual(environment["STRATA_STATUS_FILE"], "STRATA_PS5_STATUS.json")
        self.assertEqual(environment["STRATA_STATUS_MD_FILE"], "")
        self.assertEqual(json.loads(environment["STRATA_ALLOWED_TASK_TYPES"]), ["PS5"])
        self.assertEqual(environment["STRATA_MAX_TASK_OUTPUT_TOKENS"], "20000")

    def test_worker_entrypoint_activates_only_after_profile_validation(self):
        with patch.dict(os.environ, {}, clear=False):
            profile = prepare_worker(self.profile_path, current_root=self.repo,
                                     current_branch="research/ps5-firmware")

            self.assertEqual(profile.worker_id, "ps5")
            self.assertEqual(os.environ["STRATA_WORKER_BRANCH"], "research/ps5-firmware")
            self.assertEqual(os.environ["STRATA_STATUS_FILE"], "STRATA_PS5_STATUS.json")

    def test_worker_entrypoint_rejects_branch_before_activating(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STRATA_WORKER_ID", None)
            with self.assertRaisesRegex(ValueError, "current Git branch"):
                prepare_worker(self.profile_path, current_root=self.repo, current_branch="main")
            self.assertNotIn("STRATA_WORKER_ID", os.environ)


if __name__ == "__main__":
    unittest.main()
