import contextlib, copy, io, json, sys, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measurement_adapter as adapter

class MeasurementAdapterTest(unittest.TestCase):
    def test_schema_and_exact_mutations(self):
        vectors = adapter.validate()
        self.assertEqual(len(vectors["fieldOrder"]), 30)
        self.assertEqual(len(vectors["cases"]), 26)
        self.assertEqual(sum(1 + case["encode"] for case in vectors["cases"]), 47)
        self.assertTrue(next(case for case in vectors["cases"] if case["id"] == "bike-max-power")["encode"])
        case = next(c for c in vectors["cases"] if c["id"] == "minimal-treadmill")
        expected = case["decoded"]
        for key in ("flags", "present", "unavailable", "moreData", "bytesRead"):
            actual = copy.deepcopy(expected); actual[key] += 1
            self.assertFalse(adapter.exact(actual, expected), key)
        for index in (0, 3, 17, 29):
            actual = copy.deepcopy(expected); actual["values"][index] += 1
            self.assertFalse(adapter.exact(actual, expected), index)
        actual = copy.deepcopy(expected); actual.pop("truncated")
        self.assertFalse(adapter.exact(actual, expected))

    def test_runner_counts_both_directions_and_failures(self):
        vectors = adapter.validate(); fixture = {"cases": [vectors["cases"][0]]}
        output = io.StringIO()
        with mock.patch.object(adapter, "validate", return_value=fixture), \
             mock.patch.object(adapter, "call", side_effect=[fixture["cases"][0]["decoded"], {"bytes": "dead"}]), \
             contextlib.redirect_stdout(output):
            self.assertFalse(adapter.run("driver"))
        report = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual((report["cases"], report["assertions"], report["passed"], report["failed"]), (1, 2, 1, 1))
        self.assertEqual(report["outcomes"][1]["direction"], "encode")

    def test_runner_error_is_not_green(self):
        output = io.StringIO()
        with mock.patch.object(adapter, "validate", side_effect=ValueError("bad schema")), contextlib.redirect_stdout(output):
            self.assertFalse(adapter.run("driver"))
        self.assertEqual(json.loads(output.getvalue().split("] ", 1)[1])["runnerErrors"], ["bad schema"])

if __name__ == "__main__": unittest.main()
