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
        for name in ("ENDURANCE", "RECOVERIES", "REVIEW_LOG"):
            patcher = patch.object(daemon, name, base / f"{name}.json")
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_inbox_scope_and_duplicate(self):
        task = {"id": "IN-XRE03-1", "area": "XRE03", "branch": "research/xbox-firmware",
                "objective": "Review a public XVD header format without reading binary firmware.",
                "sources": ["README.md"],
                "allowed_writes": ["docs/research/xbox-inbox-note.md"]}
        imported = daemon.validate_incoming(task, task["branch"])
        self.assertEqual(imported["origin"], "github_inbox")
        self.assertEqual(imported["sources"], ["README.md"])
        self.assertEqual(imported["task_type"], "XBOX")
        with self.assertRaises(ValueError):
            daemon.validate_incoming(dict(task, allowed_writes=["driver/kmd/entry.c"]), task["branch"])
        with self.assertRaises(ValueError):
            daemon.validate_incoming(dict(task, branch="main"), "main")
        with patch.object(daemon, "get_content", return_value=(json.dumps({"schema_version": 1, "tasks": [task, task]}), "sha")):
            self.assertEqual(daemon.import_inbox("owner/repo", task["branch"]), 1)
            self.assertEqual(daemon.import_inbox("owner/repo", task["branch"]), 0)
        self.assertEqual(len(daemon.load(daemon.INBOX_QUEUE)["tasks"]), 1)

    def test_nagi_inbox_task_is_accepted_only_by_scoped_worker(self):
        task = {"id": "IN-NAGI-001", "area": "NAGI", "branch": "agent/strata-nagi",
                "objective": "Summarize the documented Nagi build blocker from the listed source files.",
                "sources": ["driver/kmd/bc250kmd.inf", "docs/build.md"],
                "allowed_writes": ["docs/research/strata/nagi-build-blocker-review.md"]}
        with patch.object(daemon, "APPROVED_AREAS", {"NAGI"}), \
                patch.object(daemon, "APPROVED_TYPES", {"NAGI"}):
            imported = daemon.validate_incoming(task, task["branch"])
            self.assertEqual(imported["task_type"], "NAGI")
            self.assertEqual(imported["branch"], "agent/strata-nagi")
            with self.assertRaises(ValueError):
                daemon.validate_incoming(dict(task, allowed_writes=["driver/kmd/unauthorized.inf"]),
                                         task["branch"])
            with self.assertRaises(ValueError):
                daemon.validate_incoming(dict(task, branch="research/ps5-firmware"),
                                         "research/ps5-firmware")

    def test_inbox_import_ignores_tasks_owned_by_other_workers(self):
        task = {"id": "IN-XRE03-OWNED-ELSEWHERE", "area": "XRE03",
                "branch": "research/xbox-firmware",
                "objective": "Summarize documented XVD metadata from the listed source file.",
                "sources": ["README.md"],
                "allowed_writes": ["docs/research/xbox-owner-note.md"]}
        payload = json.dumps({"schema_version": 1, "tasks": [task]})
        with patch.object(daemon, "get_content", return_value=(payload, "sha")):
            self.assertEqual(daemon.import_inbox("owner/repo", "research/ps5-firmware"), 0)
        self.assertEqual(daemon.load(daemon.INBOX_QUEUE)["tasks"], [])
        self.assertEqual(daemon.load(daemon.REJECTIONS)["tasks"], [])

    def test_inbox_rejects_missing_or_unbounded_sources(self):
        task = {"id": "IN-RE03-2", "area": "RE03", "branch": "research/ps5-firmware",
                "objective": "Compare documented PS5 ELF loader metadata without reading firmware bytes.",
                "sources": ["README.md"],
                "allowed_writes": ["docs/research/ps5-loader-followup.md"]}
        with self.assertRaisesRegex(ValueError, "sources"):
            daemon.validate_incoming({key: value for key, value in task.items() if key != "sources"}, task["branch"])
        for source in ("../README.md", "scratch/private.txt", "missing-source.md",
                       "https://example.org/format", "https://user@github.com/example/repo"):
            with self.assertRaises(ValueError):
                daemon.validate_incoming(dict(task, sources=[source]), task["branch"])

    def test_inbox_rejects_duplicate_source_paths(self):
        task = {"id": "IN-RE03-3", "area": "RE03", "branch": "research/ps5-firmware",
                "objective": "Compare documented PS5 loader metadata without reading firmware bytes.",
                "sources": ["README.md", "README.md"],
                "allowed_writes": ["docs/research/ps5-loader-followup.md"]}
        with self.assertRaisesRegex(ValueError, "unique"):
            daemon.validate_incoming(task, task["branch"])

    def test_public_url_sources_require_and_expose_fetch_url(self):
        url = "https://raw.githubusercontent.com/example/repo/main/README.md"
        task = {"id": "IN-RE03-URL-1", "area": "RE03", "branch": "research/ps5-firmware",
                "objective": "Compare public PS5 ELF type labels without reading firmware binaries.",
                "sources": [url], "allowed_writes": ["docs/research/ps5-elf-types.md"]}
        with self.assertRaisesRegex(ValueError, "allow_public_fetch"):
            daemon.validate_incoming(task, task["branch"])

        task["allow_public_fetch"] = True
        imported = daemon.validate_incoming(task, task["branch"])
        self.assertTrue(imported["allow_public_fetch"])
        names = {item["function"]["name"] for item in worker.definitions(imported)}
        self.assertEqual(names, {"fetch_url", "write_file"})

    def test_public_url_fetch_opt_in_must_be_boolean(self):
        task = {"id": "IN-RE03-URL-2", "area": "RE03", "branch": "research/ps5-firmware",
                "objective": "Compare public PS5 ELF type labels without reading firmware binaries.",
                "sources": ["https://raw.githubusercontent.com/example/repo/main/README.md"],
                "allowed_writes": ["docs/research/ps5-elf-types.md"], "allow_public_fetch": "yes"}
        with self.assertRaisesRegex(ValueError, "boolean"):
            daemon.validate_incoming(task, task["branch"])

    def test_generated_public_source_task_exposes_fetch_url(self):
        with patch.object(daemon, "generated_sources_available", return_value=True):
            task = daemon.generate_task("research/xbox-firmware")
        names = {item["function"]["name"] for item in worker.definitions(task)}
        self.assertIn("fetch_url", names)
        self.assertIn("read_file", names)
        self.assertTrue(task["allow_public_fetch"])

    def test_generated_nagi_task_uses_a_bounded_host_test_source_set(self):
        task = daemon.generate_task("agent/strata-nagi")
        self.assertEqual(task["area"], "NAGI")
        self.assertEqual(task["task_type"], "NAGI")
        self.assertEqual(task["sources"], ["driver/kmd/adapter_owner.c",
                                            "driver/kmd/adapter_owner.h",
                                            "driver/kmd/test/adapter_owner_test.c"])
        self.assertEqual(task["allowed_writes"], [
            "docs/research/strata/nagi-adapter-owner-coverage-review.md"])
        self.assertIsNone(daemon.generate_task("agent/strata-nagi"))

    def test_generated_task_is_skipped_when_a_local_source_is_missing(self):
        template = {"id": "AUTO-NAGI-MISSING-SOURCE", "area": "NAGI", "task_type": "NAGI",
                    "branch": "agent/strata-nagi", "objective": "Review a bounded missing-source case.",
                    "sources": ["driver/kmd/does-not-exist.c"],
                    "allowed_writes": ["docs/research/strata/nagi-missing-source.md"]}
        with patch.object(daemon, "GENERATED", [template]):
            self.assertIsNone(daemon.generate_task("agent/strata-nagi"))

    def test_task_scoped_tool_schema_hides_terminal(self):
        tools = worker.definitions({"sources": ["README.md"], "allowed_writes": ["docs/research/x.md"]})
        names = {item["function"]["name"] for item in tools}
        self.assertEqual(names, {"read_file", "write_file"})

    def test_unauthorized_terminal_is_not_exposed(self):
        task = {"sources": ["README.md"], "allowed_writes": ["docs/research/x.md"]}
        self.assertNotIn("terminal", {item["function"]["name"] for item in worker.definitions(task)})

    def test_metadata_check_can_list_only_its_declared_glob(self):
        tools = worker.definitions({"sources": [], "tools": ["list_files", "write_file"],
                                    "allowed_writes": ["docs/research/result.md"]})
        self.assertEqual({item["function"]["name"] for item in tools}, {"list_files", "write_file"})

    def test_generated_task_and_checkpoint_recovery(self):
        with patch.object(daemon, "generated_sources_available", return_value=True):
            task = daemon.generate_task("research/xbox-firmware")
        self.assertEqual(task["origin"], "generated")
        with patch.object(daemon, "generated_sources_available", return_value=True):
            self.assertEqual(daemon.generate_task("research/xbox-firmware")["id"], "AUTO-XRE06-01")
        queue = daemon.load(daemon.GENERATED_QUEUE)
        queue["tasks"][0]["status"] = "running"
        daemon.save(daemon.GENERATED_QUEUE, queue)
        path, selected = daemon.next_task("research/xbox-firmware")
        self.assertEqual(path, daemon.GENERATED_QUEUE)
        self.assertEqual(selected["id"], "AUTO-XRE03-01")

    def test_retry_scheduled_task_is_selected_after_delay(self):
        task = {"id": "T-retry", "branch": "agent/strata-v2", "status": "retry_scheduled",
                "retry_at": 0, "objective": "retry"}
        path = Path(self.temp.name) / "TASK_QUEUE.json"
        daemon.save(path, {"schema_version": 1, "tasks": [task]})
        with patch.object(daemon, "ROOT", Path(self.temp.name)):
            selected_path, selected = daemon.next_task("agent/strata-v2")
        self.assertEqual(selected_path, path)
        self.assertEqual(selected["id"], "T-retry")

    def test_strata_backlog_replenishes_to_floor_and_runs_root_queue(self):
        base = Path(self.temp.name)
        root_queue = base / "TASK_QUEUE.json"
        objectives = base / "STRATA_OBJECTIVES.json"
        (base / "README.md").write_text("source fixture\n", encoding="utf-8")
        daemon.save(root_queue, {"schema_version": 1, "tasks": []})
        daemon.save(objectives, {"schema_version": 1, "tasks": [
            {"id": f"T-{i}", "objective": f"Review source {i}", "area": "PS5",
             "sources": ["README.md"], "allowed_writes": [f"docs/research/t{i}.md"],
             "tools": ["read_file", "write_file"]} for i in range(23)
        ]})
        with patch.object(daemon, "ROOT", base), patch.object(daemon, "OBJECTIVES", objectives):
            self.assertEqual(daemon.replenish_backlog("agent/strata-v2", floor=20), 20)
            self.assertEqual(daemon.replenish_backlog("agent/strata-v2", floor=20), 0)
            path, task = daemon.next_task("agent/strata-v2")
        self.assertEqual(path, root_queue)
        self.assertEqual(task["id"], "T-0")

    def test_replenishment_preserves_explicit_publication_policy(self):
        base = Path(self.temp.name)
        root_queue = base / "TASK_QUEUE.json"
        objectives = base / "STRATA_OBJECTIVES.json"
        (base / "tools").mkdir()
        (base / "tools/strata_daemon.py").write_text("source fixture\n", encoding="utf-8")
        daemon.save(root_queue, {"schema_version": 1, "tasks": []})
        daemon.save(objectives, {"schema_version": 1, "tasks": [{
            "id": "CODE-1", "objective": "Implement and test.", "area": "STRATA",
            "sources": ["tools/strata_daemon.py"], "allowed_writes": ["tools/test_strata_daemon.py"],
            "publish": True, "publication_policy": "unit-tested-code",
            "verify": [["python", "-m", "unittest", "tools.test_strata_daemon"]]}]})
        with patch.object(daemon, "ROOT", base), patch.object(daemon, "OBJECTIVES", objectives):
            daemon.replenish_backlog("agent/strata-v2", floor=1)
        self.assertTrue(daemon.load(root_queue)["tasks"][0]["publish"])

    def test_profile_backlog_routes_only_matching_area_and_branch(self):
        base = Path(self.temp.name)
        queue = base / "profile-queue.json"
        objectives = base / "STRATA_OBJECTIVES.json"
        (base / "source.md").write_text("source fixture\n", encoding="utf-8")
        daemon.save(queue, {"schema_version": 1, "tasks": []})
        daemon.save(objectives, {"schema_version": 1, "tasks": [
            {"id": "NAGI-1", "area": "NAGI", "objective": "Inspect a Nagi build dependency.",
             "sources": ["source.md"], "allowed_writes": ["out/nagi.md"]},
            {"id": "PS5-1", "area": "PS5", "objective": "Summarize PS5 metadata.",
             "sources": ["source.md"], "allowed_writes": ["out/ps5.md"]},
            {"id": "PS5-2", "area": "RE02", "objective": "Inspect a bounded PS5 metadata report.",
             "sources": ["source.md"], "allowed_writes": ["out/re02.md"]},
        ]})
        with patch.object(daemon, "ROOT", base), patch.object(daemon, "QUEUE", queue), \
                patch.object(daemon, "OBJECTIVES", objectives), \
                patch.object(daemon, "APPROVED_AREAS", {"NAGI"}), \
                patch.object(daemon, "APPROVED_TYPES", {"NAGI"}), \
                patch.object(daemon, "worker_profile_active", return_value=True):
            self.assertEqual(daemon.replenish_backlog("agent/strata-nagi", floor=10), 1)
            tasks = daemon.load(queue)["tasks"]
        self.assertEqual([task["id"] for task in tasks], ["NAGI-1"])
        self.assertEqual(tasks[0]["branch"], "agent/strata-nagi")

    def test_worker_retry_is_not_overwritten_by_daemon(self):
        task = {"id": "T-retry", "branch": "agent/strata-v2", "status": "retry_scheduled",
                "attempts": 1, "error": "model API timeout"}
        path = Path(self.temp.name) / "root.json"
        daemon.save(path, {"schema_version": 1, "tasks": [task]})
        daemon.update_failure(path, task)
        saved = daemon.load(path)["tasks"][0]
        self.assertEqual(saved["status"], "retry_scheduled")
        self.assertEqual(saved["attempts"], 1)

    def test_unexpected_worker_exit_is_rescheduled_then_quarantined(self):
        path = Path(self.temp.name) / "worker-exit.json"
        task = {"id": "T-worker-exit", "branch": "agent/strata-v2", "status": "running"}
        daemon.save(path, {"schema_version": 1, "tasks": [task]})
        for attempt in range(3):
            daemon.update_failure(path, task)
            saved = daemon.load(path)["tasks"][0]
            self.assertEqual(saved["status"], "pending")
            self.assertEqual(saved["attempts"], attempt + 1)
            if attempt == 0:
                self.assertGreater(saved["retry_at"] - __import__("time").time(), 80)
            task = saved
        daemon.update_failure(path, task)
        self.assertEqual(daemon.load(path)["tasks"][0]["status"], "blocked")

    def test_independent_task_runs_before_delayed_retry(self):
        now = __import__("time").time()
        tasks = [
            {"id": "T-retry", "branch": "agent/strata-v2", "status": "pending", "retry_at": now + 90},
            {"id": "T-next", "branch": "agent/strata-v2", "status": "pending", "retry_at": 0},
        ]
        path = Path(self.temp.name) / "TASK_QUEUE.json"
        daemon.save(path, {"schema_version": 1, "tasks": tasks})
        with patch.object(daemon, "ROOT", Path(self.temp.name)):
            _, selected = daemon.next_task("agent/strata-v2")
        self.assertEqual(selected["id"], "T-next")

    def test_review_generation_is_disabled_to_prevent_review_loops(self):
        base = Path(self.temp.name)
        (base / "source.md").write_text("Source claim.\n", encoding="utf-8")
        output = base / "docs/research/strata/result.md"
        output.parent.mkdir(parents=True)
        output.write_text("Result note.\n", encoding="utf-8")
        task = {"id": "P-1", "branch": "agent/strata-v2", "status": "done", "area": "PS5",
                "sources": ["source.md"], "allowed_writes": ["docs/research/strata/result.md"]}
        queue_path = base / "TASK_QUEUE.json"
        daemon.save(queue_path, {"schema_version": 1, "tasks": [task]})
        with patch.object(daemon, "ROOT", base):
            self.assertEqual(daemon.generate_followup_reviews("agent/strata-v2", floor=5), 0)
            self.assertEqual(daemon.generate_followup_reviews("agent/strata-v2", floor=5), 0)
        result = daemon.load(queue_path)["tasks"]
        self.assertEqual([item["id"] for item in result], ["P-1"])

    def test_scheduler_rotates_between_independent_areas(self):
        base = Path(self.temp.name)
        root = base / "TASK_QUEUE.json"
        daemon.save(root, {"schema_version": 1, "tasks": [
            {"id": "PS5-1", "branch": "agent/strata-v2", "area": "PS5", "status": "pending"},
            {"id": "PS5-2", "branch": "agent/strata-v2", "area": "PS5", "status": "pending"},
            {"id": "NAGI-1", "branch": "agent/strata-v2", "area": "NAGI", "status": "pending"},
        ]})
        with patch.object(daemon, "ROOT", base), patch.object(daemon, "AREA_ROTATION", base / "rotation.json"):
            first = daemon.next_task("agent/strata-v2")[1]
            second = daemon.next_task("agent/strata-v2")[1]
        self.assertEqual((first["area"], second["area"]), ("PS5", "NAGI"))

    def test_simulated_api_failure_persists_retry_and_returns(self):
        base = Path(self.temp.name)
        queue = base / "queue.json"
        task = {"id": "T-api-fail", "branch": "agent/strata-v2", "status": "running",
                "objective": "Read a declared source", "allowed_writes": ["docs/research/test.md"]}
        worker.atomic_json(queue, {"schema_version": 1, "tasks": [task]})
        paths = {name: base / f"{name}.json" for name in ("STATE_DB", "MEMORY", "CHECKPOINT", "METRICS")}
        args = ["strata_supervisor.py", "--once", "--queue", str(queue), "--task-id", task["id"]]
        with patch.object(worker, "active_model", return_value="mock-model"), \
             patch.object(worker, "current_branch", return_value="agent/strata-v2"), \
             patch.object(worker, "api", side_effect=TimeoutError("simulated API timeout")), \
             patch.object(worker.sys, "argv", args), \
             patch.multiple(worker, **paths):
            self.assertEqual(worker.main(), 1)
        saved = json.loads(queue.read_text(encoding="utf-8"))["tasks"][0]
        self.assertEqual(saved["status"], "retry_scheduled")
        self.assertIn("simulated API timeout", saved["error"])

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

    def test_project_firmware_analysis_python_is_scoped_source(self):
        path = worker.confined("tools/firmware/elf_inventory_summary.py")
        self.assertEqual(path.name, "elf_inventory_summary.py")

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
        with patch.object(daemon, "git", side_effect=lambda *args: "0" if args[0] == "rev-list" else "deadbeef"), \
             patch.object(daemon, "put_content", side_effect=lambda *args: captured.append(args)):
            payload = daemon.heartbeat("owner/repo", "research/xbox-firmware", "idle", None)
        self.assertEqual(len(captured), 2)
        self.assertEqual({item[2] for item in captured}, {"AGENT_STATUS.json", "AGENT_STATUS.md"})
        for field in ("utc", "state", "current_task_id", "research_area", "completed_count", "failed_count",
                      "tool_calls", "input_tokens", "output_tokens", "last_successful_validation_utc",
                      "last_successful_commit", "next_task_id"):
            self.assertIn(field, payload)

    def test_profile_heartbeat_writes_only_its_private_status_file(self):
        captured = []
        env = {"STRATA_STATUS_BRANCH": "agent/strata-status",
               "STRATA_STATUS_FILE": "STRATA_PS5_STATUS.json", "STRATA_STATUS_MD_FILE": ""}
        with patch.dict("os.environ", env), \
             patch.object(daemon, "git", side_effect=lambda *args: "0" if args[0] == "rev-list" else "deadbeef"), \
             patch.object(daemon, "put_content", side_effect=lambda *args: captured.append(args)):
            daemon.heartbeat("owner/repo", "research/ps5-firmware", "idle", None)

        self.assertEqual([item[2] for item in captured], ["STRATA_PS5_STATUS.json"])

    def test_status_publication_retries_concurrent_branch_update(self):
        previous = [(None, None), (None, "new-head-file-sha")]
        with patch.object(daemon, "get_content", side_effect=previous), \
                patch.object(daemon, "gh_api", side_effect=[RuntimeError("HTTP 409 conflict"), {}]) as api:
            self.assertTrue(daemon.put_content("owner/repo", "agent/strata-status",
                                               "STRATA_NAGI_STATUS.json", "{}\n", "status"))
        self.assertEqual(api.call_count, 2)
        self.assertNotIn("sha", api.call_args_list[0].args[3])
        self.assertEqual(api.call_args_list[1].args[3]["sha"], "new-head-file-sha")

    def test_worker_type_and_area_scope_blocks_cross_project_tasks(self):
        env = {"STRATA_ALLOWED_TASK_TYPES": '["PS5"]', "STRATA_ALLOWED_AREAS": '["RE03"]'}
        with patch.dict("os.environ", env):
            self.assertTrue(worker.task_in_worker_scope({"area": "RE03", "task_type": "PS5"}))
            self.assertFalse(worker.task_in_worker_scope({"area": "XRE03", "task_type": "XBOX"}))
            self.assertFalse(worker.task_in_worker_scope({"area": "RE04", "task_type": "PS5"}))

    def test_nagi_worker_scope_infers_nagi_task_type(self):
        env = {"STRATA_ALLOWED_TASK_TYPES": '["NAGI"]', "STRATA_ALLOWED_AREAS": '["NAGI"]'}
        with patch.dict("os.environ", env):
            self.assertTrue(worker.task_in_worker_scope({"area": "NAGI"}))
            self.assertFalse(worker.task_in_worker_scope({"area": "RE03"}))

    def test_task_command_uses_supervisor_from_v3_source_root(self):
        command = daemon.task_command(Path(self.temp.name) / "inbox.json", "IN-RE03-4")
        self.assertEqual(Path(command[1]), daemon.CODE_ROOT / "tools/strata_supervisor.py")
        self.assertEqual(command[-1], "IN-RE03-4")

    def test_task_log_path_uses_worker_log_directory_and_safe_id(self):
        path = daemon.task_log_path({"id": "IN-RE03-4"})

        self.assertEqual(path.parent, daemon.LOG_DIR)
        self.assertEqual(path.name, "IN-RE03-4.log")
        with self.assertRaisesRegex(ValueError, "task ID"):
            daemon.task_log_path({"id": "../../AGENT_STATUS"})

    def test_compaction_keeps_more_than_sixteen_rounds_bounded(self):
        state = {"calls": 0, "max_messages": 0}

        def fake_api(messages, _model, _task, step=None):
            state["calls"] += 1
            state["max_messages"] = max(state["max_messages"], len(messages))
            if state["calls"] <= 17:
                return {"message": {"role": "assistant", "content": None, "tool_calls": [
                    {"id": f"call{state['calls']}", "type": "function",
                     "function": {"name": "terminal", "arguments": json.dumps({"argv": ["rg", "-n", f"compaction-{state['calls']}", "README.md"]})}}]}}
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
