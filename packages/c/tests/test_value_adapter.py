import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import value_adapter as adapter


class ValueAdapterTests(unittest.TestCase):
    def test_schema_rejects_extra_fields_and_duplicate_ids(self):
        import jsonschema
        vectors = adapter.validate()
        schema = json.loads((adapter.VALUES / "schema.json").read_text())
        changed = copy.deepcopy(vectors)
        changed["cases"][0]["unexpected"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(changed, schema)
        changed = copy.deepcopy(vectors)
        changed["cases"].append(changed["cases"][0])
        original_loads = json.loads
        def load(text):
            parsed = original_loads(text)
            return changed if "cases" in parsed else parsed
        with mock.patch.object(adapter.json, "loads", side_effect=load), self.assertRaisesRegex(ValueError, "duplicate"):
            adapter.validate()

    def test_wrong_bytes_kind_unit_divisor_and_values_fail_runner(self):
        case = next(c for c in adapter.validate()["cases"] if c["operation"] == "range")
        correct_decode = ["ok", case["kind"], *map(str, [case["minimum"], case["maximum"], case["increment"], case["scaleDivisor"], case["unit"]])]
        correct_encode = ["ok", bytes(case["expectedBytes"]).hex(), str(len(case["expectedBytes"]))]
        mutations = [(0, 1)] + [(1, i) for i in range(1, 7)]
        for direction, field in mutations:
            responses = [correct_encode.copy(), correct_decode.copy()]
            responses[direction][field] = "wrong"
            with self.subTest(direction=direction, field=field), \
                 mock.patch.object(adapter, "validate", return_value={"cases": [case]}), \
                 mock.patch.object(adapter, "invoke", side_effect=responses), contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(adapter.run("encode", "decode"))

    def test_runner_error_is_not_success(self):
        with mock.patch.object(adapter, "validate", side_effect=ValueError("bad fixture")), contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(adapter.run("encode", "decode"))


if __name__ == "__main__":
    unittest.main()
