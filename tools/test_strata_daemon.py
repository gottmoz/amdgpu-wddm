"""Host-only checks for the continuous Strata coordinator."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import strata_daemon as daemon
import strata_supervisor as worker


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.paths = [base / name for name in ("inbox.json", "xbox.json", "generated.json", "rejected.json")]
        for name, path in zip(("INBOX_QUEUE", "XBOX_QUEUE", "GENERATED_QUEUE", "REJECTIONS"), self.paths):
            patcher = patch.object(daemon, name, path)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_inbox_scope_and_duplicate(self):
        task = {"id": "IN-XRE03-1", "area": "XRE03", "branch": "research/xbox-firmware",
                "objective": "Review a public XVD header format without reading binary firmware.",
                "allowed_writes": ["docs/research/xbox-inbox-note.md"]}
        self.assertEqual(daemon.validate_incoming(task, task["branch"])["origin"], "github_inbox")
        with self.assertRaises(ValueError):
            daemon.validate_incoming(dict(task, allowed_writes=["driver/kmd/entry.c"]), task["branch"])
        with self.assertRaises(ValueError):
            daemon.validate_incoming(dict(task, branch="main"), "main")
        with patch.object(daemon, "get_content", return_value=(json.dumps({"schema_version": 1, "tasks": [task, task]}), "sha")):
            self.assertEqual(daemon.import_inbox("owner/repo", task["branch"]), 1)
            self.assertEqual(daemon.import_inbox("owner/repo", task["branch"]), 0)
        self.assertEqual(len(daemon.load(daemon.INBOX_QUEUE)["tasks"]), 1)

    def test_generated_task_and_checkpoint_recovery(self):
        task = daemon.generate_task("research/xbox-firmware")
        self.assertEqual(task["origin"], "generated")
        self.assertEqual(daemon.generate_task("research/xbox-firmware")["id"], "AUTO-XRE06-01")
        queue = daemon.load(daemon.GENERATED_QUEUE)
        queue["tasks"][0]["status"] = "running"
        daemon.save(daemon.GENERATED_QUEUE, queue)
        path, selected = daemon.next_task("research/xbox-firmware")
        self.assertEqual(path, daemon.GENERATED_QUEUE)
        self.assertEqual(selected["id"], "AUTO-XRE03-01")

    def test_source_scoped_task_rejects_unrelated_reads(self):
        task = {"sources": ["XBOX_FIRMWARE_INVENTORY.json"], "allowed_writes": ["docs/research/test.md"]}
        with self.assertRaisesRegex(ValueError, "declared task source"):
            worker.tool("read_file", {"path": "PROGRESS.md"}, task)
        with self.assertRaisesRegex(ValueError, "source-scoped"):
            worker.tool("list_files", {"glob": "docs/**/*.md"}, task)

    def test_public_microcode_manifest_is_read_only(self):
        path = worker.confined("tools/firmware/cyan_skillfish2.json")
        self.assertEqual(path.name, "cyan_skillfish2.json")
        with self.assertRaisesRegex(ValueError, "outside allowed"):
            worker.confined("tools/firmware/cyan_skillfish2.json", writable=True)

    def test_budget_split_and_retry_limit(self):
        task = {"id": "AUTO-test", "area": "XRE03", "branch": "research/xbox-firmware",
                "objective": "Read two sources", "allowed_writes": ["docs/research/test-note.md"],
                "sources": ["one.md", "two.md"], "status": "blocked", "error": "tool round limit reached"}
        daemon.save(daemon.GENERATED_QUEUE, {"schema_version": 1, "tasks": [task]})
        daemon.update_failure(daemon.GENERATED_QUEUE, task)
        result = daemon.load(daemon.GENERATED_QUEUE)["tasks"]
        self.assertEqual(result[0]["status"], "split")
        self.assertEqual([item["id"] for item in result[1:]], ["AUTO-test-P1", "AUTO-test-P2"])
        stalled = {"id": "IN-test", "branch": "research/xbox-firmware", "objective": "read source",
                   "allowed_writes": ["docs/research/test.md"], "status": "running"}
        daemon.save(daemon.INBOX_QUEUE, {"schema_version": 1, "tasks": [stalled]})
        for attempt in range(3):
            daemon.update_failure(daemon.INBOX_QUEUE, stalled, stalled=True)
            result = daemon.load(daemon.INBOX_QUEUE)["tasks"][0]
            self.assertEqual(result["status"], "pending")
        daemon.update_failure(daemon.INBOX_QUEUE, stalled, stalled=True)
        self.assertEqual(daemon.load(daemon.INBOX_QUEUE)["tasks"][0]["status"], "blocked")

    def test_heartbeat_has_required_fields(self):
        captured = []
        with patch.object(daemon, "put_content", side_effect=lambda *args: captured.append(args)):
            payload = daemon.heartbeat("owner/repo", "research/xbox-firmware", "idle", None)
        self.assertEqual(len(captured), 2)
        self.assertEqual({item[2] for item in captured}, {"AGENT_STATUS.json", "AGENT_STATUS.md"})
        for field in ("utc", "state", "current_task_id", "research_area", "completed_count", "failed_count",
                      "tool_calls", "input_tokens", "output_tokens", "last_successful_validation_utc",
                      "last_successful_commit", "next_task_id"):
            self.assertIn(field, payload)

    def test_compaction_keeps_more_than_sixteen_rounds_bounded(self):
        state = {"calls": 0, "max_messages": 0}

        def fake_api(messages, _model, _task):
            state["calls"] += 1
            state["max_messages"] = max(state["max_messages"], len(messages))
            if state["calls"] <= 17:
                return {"message": {"role": "assistant", "content": None, "tool_calls": [
                    {"id": f"call{state['calls']}", "type": "function",
                     "function": {"name": "terminal", "arguments": '{"argv":["git","status"]}'}}]}}
            return {"message": {"role": "assistant", "content": "done"}}

        checkpoint = Path(self.temp.name) / "checkpoint.json"
        metrics = Path(self.temp.name) / "metrics.json"
        with patch.object(worker, "api", side_effect=fake_api), patch.object(worker, "tool", return_value={"exit_code": 0}), \
             patch.object(worker, "CHECKPOINT", checkpoint), patch.object(worker, "METRICS", metrics):
            result = worker.work({"id": "smoke", "objective": "prove more than 16 rounds", "allowed_writes": [], "tools": ["terminal"]}, "fake")
        self.assertEqual(result, "done")
        self.assertEqual(state["calls"], 18)
        self.assertLess(state["max_messages"], 30)
        self.assertTrue(checkpoint.exists())


if __name__ == "__main__":
    unittest.main()

