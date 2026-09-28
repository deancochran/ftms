import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capability_adapter as adapter


class CapabilityCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = adapter.load_cases()
        cls.vectors = json.loads((adapter.CORPUS / "vectors.json").read_text())
        cls.schema = json.loads((adapter.CORPUS / "schema.json").read_text())

    def test_schema_and_unique_expanded_ids(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("duplicate-feature-no-first-win", ids)
        self.assertIn("power-range-absent-not-heart-rate", ids)
        self.assertEqual(len({case["category"] for case in self.cases}), 8)
        for case in self.cases:
            self.assertEqual(case["expected"]["observationCount"], len(case["expected"]["observations"]))
            self.assertEqual(case["expected"]["diagnosticCount"], len(case["expected"]["diagnostics"]))

    def test_exact_self_and_key_order(self):
        for case in self.cases:
            self.assertIsNone(adapter.compare(dict(reversed(list(case["expected"].items()))), case["expected"]))

    def test_wrong_scalar_or_tuple_field_rejected(self):
        expected = self.cases[0]["expected"]
        paths = [
            ["generation"], ["discovery"], ["scope"], ["observationCount"], ["diagnosticCount"],
            ["presence", 1], ["feature", 0], ["feature", 1], ["feature", 2],
            *[["feature", i] for i in range(3, 7)],
            *[["ranges", 4, 3, i] for i in range(6)],
            *[["operations", 5, i] for i in range(6)],
            ["observations", 0, 0], ["observations", 0, 2], ["observations", 0, 3],
            ["observations", 0, 4], ["observations", 0, 5], ["observations", 0, 6],
        ]
        for path in paths:
            with self.subTest(path=path):
                actual = copy.deepcopy(expected)
                node = actual
                for part in path[:-1]:
                    node = node[part]
                node[path[-1]] += 1
                self.assertIsNotNone(adapter.compare(actual, expected))

    def test_unknown_uuid_and_dropped_observation_rejected(self):
        expected = next(case["expected"] for case in self.cases if case["id"] == "unknown-uuid-lookalike")
        actual = copy.deepcopy(expected)
        actual["observations"][1][1] = "00002acc00001000800000805f9b34fb"
        self.assertIsNotNone(adapter.compare(actual, expected))
        actual = copy.deepcopy(expected)
        actual["observations"].pop()
        self.assertIsNotNone(adapter.compare(actual, expected))

    def test_missing_extra_and_reordered_fields_rejected(self):
        expected = self.cases[0]["expected"]
        actual = copy.deepcopy(expected)
        del actual["feature"]
        self.assertIsNotNone(adapter.compare(actual, expected))
        actual = copy.deepcopy(expected)
        actual["canExecute"] = True
        self.assertIsNotNone(adapter.compare(actual, expected))
        actual = copy.deepcopy(expected)
        actual["ranges"].reverse()
        self.assertIsNotNone(adapter.compare(actual, expected))

    def test_diagnostic_code_kind_index_and_omission_rejected(self):
        expected = next(case["expected"] for case in self.cases if case["id"] == "mandatory-feature-absent")
        for index, value in [(0, 0), (1, 15), (2, 0)]:
            actual = copy.deepcopy(expected)
            actual["diagnostics"][0][index] = value
            self.assertIsNotNone(adapter.compare(actual, expected))
        actual = copy.deepcopy(expected)
        actual["diagnostics"] = []
        self.assertIsNotNone(adapter.compare(actual, expected))

    def test_bool_and_float_not_equal_to_integer(self):
        self.assertIsNotNone(adapter.compare(True, 1))
        self.assertIsNotNone(adapter.compare(1.0, 1))
        self.assertIsNotNone(adapter.compare(0, None))

    def test_expansion_is_literal_and_does_not_mutate_template(self):
        templates = {"x": {"list": [[0, 1], [2, 3]], "number": 4}}
        saved = copy.deepcopy(templates)
        actual = adapter.expand({"template": "x", "edits": [
            {"path": ["list", "*", 0], "value": 8},
            {"path": ["list"], "op": "append", "value": [9, 10]},
            {"path": ["list", 1], "op": "remove"},
            {"path": ["list", [0, 1], 1], "value": 11},
        ]}, templates)
        self.assertEqual(actual, {"list": [[8, 11], [9, 11]], "number": 4})
        self.assertEqual(templates, saved)

    def test_bad_expansion_path_and_selection_rejected(self):
        for path in [["missing"], ["a", -1], ["a", 2], ["a", [0, 0]], ["a", "0"]]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                adapter.expand({"template": "x", "edits": [{"path": path, "value": 8}]}, {"x": {"a": [0, 1]}})

    def test_duplicate_ids_rejected(self):
        vectors = copy.deepcopy(self.vectors)
        vectors["cases"].append(vectors["cases"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            adapter.validate_vectors(vectors, self.schema)

    def test_malformed_input_and_expected_rejected(self):
        mutations = [
            (["snapshots", "full", "characteristics", 0, "bytes"], "abc"),
            (["snapshots", "full", "characteristics", 0, "readState"], True),
            (["snapshots", "full", "characteristics", 0, "reason"], 2),
            (["reports", "full", "feature", 0], 4),
            (["reports", "full", "operations", 5, 3], 5),
        ]
        for path, value in mutations:
            vectors = copy.deepcopy(self.vectors)
            node = vectors
            for part in path[:-1]:
                node = node[part]
            node[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(jsonschema.ValidationError):
                adapter.validate_vectors(vectors, self.schema)
        vectors = copy.deepcopy(self.vectors)
        vectors["cases"][0]["expected"]["edits"].append({"path": ["feature"], "value": [0]})
        with self.assertRaises(jsonschema.ValidationError):
            adapter.validate_vectors(vectors, self.schema)

    def test_driver_failure_and_wrong_json_are_not_passes(self):
        case = self.cases[0]
        with mock.patch.object(adapter.subprocess, "run", return_value=mock.Mock(returncode=65, stderr="invalid input")):
            self.assertIn("driver exit 65", adapter.execute_case("driver", case))
        with mock.patch.object(adapter.subprocess, "run", return_value=mock.Mock(returncode=0, stdout="{}")):
            self.assertIsNotNone(adapter.execute_case("driver", case))

    def test_partial_failure_accounting_and_exit(self):
        output = io.StringIO()
        with mock.patch.object(adapter, "load_cases", return_value=self.cases[:2]), \
             mock.patch.object(adapter, "execute_case", side_effect=[None, "bad range kind"]), \
             contextlib.redirect_stdout(output):
            self.assertEqual(adapter.main(["runner", "driver"]), 1)
        report = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual((report["total"], report["passed"], report["failed"]), (2, 1, 1))
        self.assertFalse(report["complete"])
        self.assertEqual(report["outcomes"][1]["id"], self.cases[1]["id"])
        self.assertEqual(report["failures"][0]["reason"], "bad range kind")

    def test_invalid_corpus_runner_error_not_pass(self):
        output = io.StringIO()
        with mock.patch.object(adapter, "load_cases", side_effect=ValueError("bad schema")), \
             contextlib.redirect_stdout(output):
            self.assertEqual(adapter.main(["runner", "driver"]), 1)
        report = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual(report["passed"], 0)
        self.assertFalse(report["complete"])
        self.assertEqual(report["runnerErrors"], ["bad schema"])


if __name__ == "__main__":
    unittest.main()
