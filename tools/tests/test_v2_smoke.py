"""Unit test for tools/v2_smoke.py using a temporary JSON fixture."""

import json
import os
import tempfile
import unittest

from tools.v2_smoke import top_level_keys


class V2SmokeTest(unittest.TestCase):
    def test_sorted_top_level_keys(self):
        fixture = {"zeta": 1, "alpha": 2, "mid": 3, "beta": 4}
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(fixture, handle)
            self.assertEqual(top_level_keys(path), ["alpha", "beta", "mid", "zeta"])
        finally:
            os.remove(path)

    def test_non_object_json_raises(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump([1, 2, 3], handle)
            with self.assertRaises(ValueError):
                top_level_keys(path)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
