import json
import tempfile
import unittest
from pathlib import Path

from verify import account_events


class AccountingTests(unittest.TestCase):
    def report(self, events):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events"
            path.write_text("\n".join(json.dumps(e) for e in events))
            return account_events(path, {"corpora": {"codec": {"caseIds": ["a"]}, "matrix": {}}})

    def test_missing_test_is_unsupported(self):
        result = self.report([{"type": "done", "success": True}])
        self.assertFalse(result["complete"])
        self.assertEqual(result["corpora"]["codec"]["unsupported"], 1)

    def test_skip_is_not_pass(self):
        result = self.report([
            {"type": "testStart", "test": {"id": 1, "name": "[codec/a]"}},
            {"type": "testDone", "testID": 1, "result": "success", "skipped": True},
            {"type": "done", "success": True},
        ])
        self.assertEqual(result["corpora"]["codec"]["skipped"], 1)

    def test_truncated_runner_and_duplicate_registration_fail(self):
        result = self.report([
            {"type": "testStart", "test": {"id": 1, "name": "[codec/a]"}},
            {"type": "testDone", "testID": 1, "result": "success", "skipped": False},
            {"type": "testStart", "test": {"id": 2, "name": "[codec/a]"}},
        ])
        self.assertFalse(result["complete"])
        self.assertTrue(result["runnerErrors"])


if __name__ == "__main__":
    unittest.main()
