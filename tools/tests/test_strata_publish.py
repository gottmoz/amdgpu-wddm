"""Publication gate tests; Git commands are mocked and never pushed."""
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import strata_supervisor as worker


class PublishPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        target = self.root / 'tools/tests'
        target.mkdir(parents=True)
        (target / 'sample.py').write_text('VALUE = 1\nassert VALUE == 1\n', encoding='utf-8')

    def task(self, **extra):
        result = {'id': 'PUBLISH-TEST-01', 'branch': 'agent/strata-v2', 'publication_policy': 'unit-tested-code',
                  'allowed_writes': ['tools/tests/sample.py'],
                  'verify': [['python', '-m', 'unittest', 'sample_test']],
                  'commit_message': 'test: sample'}
        result.update(extra)
        return result

    def test_success_transition_clears_stale_failure_fields(self):
        task = {'id': 'retry', 'status': 'retry_scheduled', 'error': 'old rejection',
                'validation_error': 'old lint failure', 'attempts': 2}
        worker.mark_task_success(task, 'validated')
        self.assertEqual(task['status'], 'done')
        self.assertEqual(task['summary'], 'validated')
        self.assertNotIn('error', task)
        self.assertNotIn('validation_error', task)
        self.assertEqual(task['attempts'], 2)

    def test_deterministic_publication_policy_rejection_is_reviewable_not_retried(self):
        task = {'status': 'done'}
        message = 'automatic publication rejects large deletion from an existing file'
        reason = worker.publication_review_reason(task, message)
        self.assertIsNotNone(reason)
        task['retry_at'] = 1
        self.assertTrue(worker.mark_publication_held(task, message))
        self.assertEqual(task['status'], 'done')
        self.assertEqual(task['review_status'], 'pending')
        self.assertNotIn('retry_at', task)
        self.assertIn('manual publication review', task['error'])
        self.assertIsNone(worker.publication_review_reason({'status': 'running'},
            'automatic publication rejects large deletion from an existing file'))
        self.assertIsNone(worker.publication_review_reason({'status': 'done'}, 'git push failed'))

    def test_policy_requires_explicit_allowlist(self):
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'current_branch', return_value='agent/strata-v2'), patch.object(worker, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'policy'):
                worker.publish(self.task(publication_policy=None))
            run.assert_not_called()

    def test_approved_unittest_command_accepts_python_bytecode_flag(self):
        result = worker.command({'argv': ['python', '-B', '-m', 'unittest', 'tools.tests.test_binary_audit']})
        self.assertEqual(result['exit_code'], 0)

    def test_validated_python_artifact_uses_mocked_git(self):
        def git_result(argv, timeout=120):
            if argv[1] == 'ls-files':
                return {'exit_code': 1, 'stdout': '', 'stderr': 'not tracked'}
            return {'exit_code': 0, 'stdout': 'abc123', 'stderr': ''}
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'current_branch', return_value='agent/strata-v2'), patch.object(worker, 'run', side_effect=git_result) as run:
            self.assertEqual(worker.publish(self.task()), 'abc123')
        self.assertEqual(run.call_count, 6)
        reviewed = __import__('json').loads((self.root / 'STRATA_REVIEWED.json').read_text(encoding='utf-8'))
        self.assertEqual(reviewed['reviewed_task_ids'], ['PUBLISH-TEST-01'])

    def test_doc_only_and_unvalidated_publish_are_rejected(self):
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'current_branch', return_value='agent/strata-v2'):
            with self.assertRaisesRegex(RuntimeError, 'limited'):
                worker.publish(self.task(allowed_writes=['docs/research/note.md']))
            with self.assertRaisesRegex(RuntimeError, 'unittest'):
                worker.publish(self.task(verify=[]))

    def test_secret_marker_is_rejected(self):
        (self.root / 'tools/tests/sample.py').write_text('token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"\n', encoding='utf-8')
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'current_branch', return_value='agent/strata-v2'), patch.object(worker, 'run', return_value={'exit_code': 0, 'stdout': '', 'stderr': ''}):
            with self.assertRaisesRegex(RuntimeError, 'credential'):
                worker.publish(self.task())

    def test_large_deletion_from_tracked_test_file_is_rejected(self):
        calls = []
        def git_result(argv, timeout=120):
            calls.append(argv)
            if argv[1:3] == ['diff', '--cached']:
                return {'exit_code': 0, 'stdout': '', 'stderr': ''}
            if argv[1] == 'ls-files':
                return {'exit_code': 0, 'stdout': 'tools/tests/sample.py', 'stderr': ''}
            if argv[1:2] == ['diff']:
                return {'exit_code': 0, 'stdout': '2\t90\ttools/tests/sample.py\n', 'stderr': ''}
            return {'exit_code': 0, 'stdout': 'abc123', 'stderr': ''}
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'current_branch', return_value='agent/strata-v2'), patch.object(worker, 'run', side_effect=git_result):
            with self.assertRaisesRegex(RuntimeError, 'large deletion'):
                worker.publish(self.task())
        self.assertFalse(any(argv[1] == 'add' for argv in calls))

    def test_test_artifact_without_assertions_is_rejected(self):
        (self.root / 'tools/tests/sample.py').write_text("print('source probe')\n", encoding='utf-8')
        calls = []
        def git_result(argv, timeout=120):
            calls.append(argv)
            if argv[1:3] == ['diff', '--cached']:
                return {'exit_code': 0, 'stdout': '', 'stderr': ''}
            if argv[1] == 'ls-files':
                return {'exit_code': 1, 'stdout': '', 'stderr': 'not tracked'}
            return {'exit_code': 0, 'stdout': 'abc123', 'stderr': ''}
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'current_branch', return_value='agent/strata-v2'), patch.object(worker, 'run', side_effect=git_result):
            with self.assertRaisesRegex(RuntimeError, 'assertion'):
                worker.publish(self.task())
        self.assertFalse(any(argv[1] == 'add' for argv in calls))

    def test_metrics_merge_never_moves_counters_or_validation_backwards(self):
        metrics = self.root / 'metrics.json'
        metrics.write_text('{"tool_calls": 900, "input_tokens": 4000, "output_tokens": 300, "last_validation_utc": "2026-11-26T10:18:37Z"}\n', encoding='utf-8')
        with patch.object(worker, 'METRICS', metrics), patch.dict(worker.STATS, {
            'tool_calls': 800, 'input_tokens': 3500, 'output_tokens': 280,
            'last_validation_utc': '2026-11-26T09:52:03Z'}):
            worker.persist_metrics()
        actual = __import__('json').loads(metrics.read_text(encoding='utf-8'))
        self.assertEqual(actual['tool_calls'], 900)
        self.assertEqual(actual['input_tokens'], 4000)
        self.assertEqual(actual['output_tokens'], 300)
        self.assertEqual(actual['last_validation_utc'], '2026-11-26T10:18:37Z')


if __name__ == '__main__':
    unittest.main()
