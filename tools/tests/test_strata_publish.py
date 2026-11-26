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
        (target / 'sample.py').write_text('VALUE = 1\n', encoding='utf-8')

    def task(self, **extra):
        result = {'branch': 'agent/strata-v2', 'publication_policy': 'unit-tested-code',
                  'allowed_writes': ['tools/tests/sample.py'],
                  'verify': [['python', '-m', 'unittest', 'sample_test']],
                  'commit_message': 'test: sample'}
        result.update(extra)
        return result

    def test_policy_requires_explicit_allowlist(self):
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'current_branch', return_value='agent/strata-v2'), patch.object(worker, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'policy'):
                worker.publish(self.task(publication_policy=None))
            run.assert_not_called()

    def test_validated_python_artifact_uses_mocked_git(self):
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'current_branch', return_value='agent/strata-v2'), patch.object(worker, 'run', return_value={'exit_code': 0, 'stdout': 'abc123', 'stderr': ''}) as run:
            self.assertEqual(worker.publish(self.task()), 'abc123')
        self.assertEqual(run.call_count, 5)

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


if __name__ == '__main__':
    unittest.main()
