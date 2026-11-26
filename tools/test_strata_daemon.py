"""Temporary inspection probe: verify daemon importability and helper behaviour."""

import unittest
from pathlib import Path


class ImportProbe(unittest.TestCase):
    def test_probe(self):
        try:
            import tools.strata_daemon as daemon
            print("IMPORT OK")
            print("ROOT:", daemon.ROOT)
            print("RUNTIME:", daemon.RUNTIME)
            print("REVIEW_LOG exists:", daemon.REVIEW_LOG.exists())
            print("OBJECTIVES exists:", daemon.OBJECTIVES.exists())
            print("followup:", daemon.generate_followup_reviews("research/xbox-firmware", floor=5))
            print("replenish:", daemon.replenish_backlog("research/xbox-firmware", floor=20))
        except Exception as exc:
            print("IMPORT FAILED:", type(exc).__name__, exc)
        print("lines 258-330:")
        lines = Path("tools/strata_daemon.py").read_text(encoding="utf-8").splitlines()
        for i in range(258, 331):
            print(i + 1, lines[i])


if __name__ == "__main__":
    unittest.main()
