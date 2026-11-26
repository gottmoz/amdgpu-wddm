"""Bounds and loop detection for autonomous Strata task execution."""
import sys
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import strata_supervisor as worker
import strata_daemon as daemon


class StrataLimitTests(unittest.TestCase):
    def test_default_task_budgets_match_operating_policy(self):
        limits = worker.task_limits({})
        self.assertEqual(limits["max_response_tokens"], 8192)
        self.assertEqual(limits["max_output_tokens"], 20000)
        self.assertEqual(limits["max_execution_seconds"], 900)
        self.assertEqual(limits["max_progress_stall_seconds"], 900)

    def test_task_can_set_justified_larger_budget(self):
        task = {"execution_limits": {"max_output_tokens": 40000},
                "budget_justification": "Compare three large ELF corpora and write a validated report."}
        self.assertEqual(worker.task_limits(task)["max_output_tokens"], 40000)

    def test_larger_budget_requires_justification(self):
        with self.assertRaisesRegex(ValueError, "budget_justification"):
            worker.task_limits({"execution_limits": {"max_execution_seconds": 1800}})

    def test_response_cap_respects_remaining_task_budget(self):
        task = {"output_tokens_total": 19000}
        self.assertEqual(worker.response_token_limit(task), 1000)

    def test_identical_tool_calls_are_detected(self):
        guard = worker.ToolCallGuard(limit=2)
        args = {"path": "tools/source.py"}
        self.assertFalse(guard.observe("read_file", args)["repeated_limit"])
        self.assertFalse(guard.observe("read_file", args)["repeated_limit"])
        self.assertTrue(guard.observe("read_file", args)["repeated_limit"])
        self.assertFalse(guard.observe("read_file", {"path": "tools/other.py"})["repeated_limit"])

    def test_daemon_deadline_is_based_on_elapsed_wall_time(self):
        self.assertFalse(daemon.task_timeout_reached(10, 909.9, 900))
        self.assertTrue(daemon.task_timeout_reached(10, 910, 900))

    def test_server_response_above_requested_token_cap_is_rejected_and_recorded(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self):
                return json.dumps({"usage": {"prompt_tokens": 20, "completion_tokens": 8193},
                                   "choices": [{"message": {"role": "assistant", "content": "too long"}}]}).encode()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = {"id": "TOKEN-CAP-TEST", "output_tokens_total": 0}
            old_stats = dict(worker.STATS)
            try:
                with patch.object(worker, "METRICS", root / "metrics.json"), \
                     patch.object(worker, "CHECKPOINT", root / "checkpoint.json"), \
                     patch.object(worker, "STATE_DB", root / "state.sqlite3"), \
                     patch.object(worker, "urlopen", return_value=Response()):
                    with self.assertRaisesRegex(RuntimeError, "MODEL_RESPONSE_TOKEN_LIMIT_EXCEEDED"):
                        worker.api([], "mock-model", task)
                    checkpoint = json.loads((root / "checkpoint.json").read_text(encoding="utf-8"))
                    self.assertEqual(checkpoint["status"], "response_token_limit_exceeded")
                    self.assertEqual(checkpoint["output_tokens_this_response"], 8193)
                    import sqlite3
                    db = sqlite3.connect(root / "state.sqlite3")
                    try:
                        event = db.execute("select kind,payload from events").fetchone()
                    finally:
                        db.close()
                    self.assertEqual(event[0], "model_response")
                    self.assertIn("8193", event[1])
            finally:
                worker.STATS.clear()
                worker.STATS.update(old_stats)


if __name__ == "__main__":
    unittest.main()
