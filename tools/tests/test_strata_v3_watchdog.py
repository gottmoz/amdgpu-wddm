import unittest
from pathlib import Path

from tools.strata_v3_watchdog import is_owned_worker_command, is_recovery, should_start


class StrataV3WatchdogTest(unittest.TestCase):
    def setUp(self):
        self.profile = Path("D:/BC250-Development/scratch/strata-v3/ps5/worker.json")
        self.command = [
            "C:/Python314/python.exe",
            "C:/repo/tools/strata_v3.py",
            "--profile",
            str(self.profile),
        ]

    def test_watchdog_owns_only_exact_worker_profile_command(self):
        self.assertTrue(is_owned_worker_command(self.command, self.profile))
        self.assertFalse(is_owned_worker_command(self.command[:-1] + ["D:/other/worker.json"], self.profile))
        self.assertFalse(is_owned_worker_command(["python.exe", "tools/strata_daemon.py"], self.profile))

    def test_watchdog_starts_only_when_not_stopped_and_worker_is_absent(self):
        self.assertTrue(should_start(0, worker_alive=False, stop_requested=False))
        self.assertFalse(should_start(123, worker_alive=True, stop_requested=False))
        self.assertFalse(should_start(0, worker_alive=False, stop_requested=True))

    def test_restart_is_counted_only_after_a_previous_owned_pid_died(self):
        self.assertFalse(is_recovery(0, worker_alive=False))
        self.assertFalse(is_recovery(123, worker_alive=True))
        self.assertTrue(is_recovery(123, worker_alive=False))


if __name__ == "__main__":
    unittest.main()
