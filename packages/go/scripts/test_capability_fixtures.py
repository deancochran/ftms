"""Tests of fixture mechanics, without executing protocol interpretation."""
import copy
import json
from pathlib import Path
import unittest

from jsonschema.exceptions import ValidationError
from capability_fixtures import expand, validate_cases


class ExpansionTests(unittest.TestCase):
    def test_ordered_edits_and_independent_copies(self):
        templates = {"x": {"a": [{"v": 1}, {"v": 2}], "b": []}}
        original = copy.deepcopy(templates)
        edits = [{"path": ["a", "*", "v"], "value": 5},
                 {"path": ["a", [0], "v"], "value": 7},
                 {"path": ["a", 0], "op": "remove"},
                 {"path": ["a", 0, "v"], "value": 9},
                 {"path": ["b"], "op": "append", "value": {"nested": []}}]
        actual = expand(templates, {"template": "x", "edits": edits})
        self.assertEqual(actual, {"a": [{"v": 9}], "b": [{"nested": []}]})
        actual["b"][0]["nested"].append(1)
        self.assertEqual(templates, original)
        self.assertEqual(edits[-1]["value"], {"nested": []})
        self.assertEqual(expand(templates, {"template": "x", "edits": [{"path": [], "value": 3}]}), 3)

    def test_invalid_edits_fail(self):
        base = {"x": {"a": [1, 2], "s": 3}}
        invalid = [
            {"path": ["missing"], "value": 0},
            {"path": ["a", 2], "value": 0},
            {"path": ["a", -1], "value": 0},
            {"path": ["a", "0"], "value": 0},
            {"path": ["a", True], "value": 0},
            {"path": ["s", 0], "value": 0},
            {"path": ["a", [0, 0]], "value": 0},
            {"path": ["a", []], "value": 0},
            {"path": ["a", "*"], "op": "remove"},
            {"path": ["a", [0]], "op": "append", "value": 0},
            {"path": [], "op": "remove"},
            {"path": ["s"], "op": "append", "value": 0},
            {"path": ["s"], "op": "other", "value": 0},
            {"path": ["s"]},
            {"path": ["s"], "op": "remove", "value": 0},
        ]
        for edit in invalid:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                expand(base, {"template": "x", "edits": [edit]})
        with self.assertRaises(ValueError):
            expand(base, {"template": "unknown", "edits": []})

    def test_schema_and_expanded_values_are_validated(self):
        root = Path(__file__).resolve().parents[3] / "shared/conformance/capabilities/v1"
        schema = json.loads((root / "schema.json").read_bytes())
        original = json.loads((root / "vectors.json").read_bytes())
        self.assertEqual(len(validate_cases(schema, original)), len(original["cases"]))
        for target, path, value in [("input", ["scope"], 99),
                                    ("expected", ["generation"], True)]:
            data = copy.deepcopy(original)
            data["cases"][0][target]["edits"].append({"path": path, "value": value})
            with self.subTest(target=target), self.assertRaises(ValidationError):
                validate_cases(schema, data)
        data = copy.deepcopy(original)
        data["cases"].append(copy.deepcopy(data["cases"][0]))
        with self.assertRaises(ValueError):
            validate_cases(schema, data)
        data = copy.deepcopy(original)
        data["schemaVersion"] = 2
        with self.assertRaises(ValidationError):
            validate_cases(schema, data)


if __name__ == "__main__":
    unittest.main()
