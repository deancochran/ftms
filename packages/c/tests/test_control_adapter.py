import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import control_adapter as adapter
import corpus_adapter as legacy


class ControlAdapterTest(unittest.TestCase):
    def test_exact_comparator_mutations(self):
        cases = adapter.validate()
        request = cases["requests"][2]["decoded"]
        for actual in [{"opcode": 3, "operands": [1234]}, {"opcode": 2, "operands": [123]},
                       {"opcode": 2, "operands": [1234], "extra": 0}, {"opcode": 2}]:
            self.assertFalse(adapter.exact(actual, request))
        for case in cases["responses"]:
            for field in case["decoded"]:
                actual = copy.deepcopy(case["decoded"])
                actual[field] += 1
                self.assertFalse(adapter.exact(actual, case["decoded"]))
        self.assertFalse(adapter.exact(True, 1))
        self.assertFalse(adapter.exact({"error": 3}, {"error": 2}))

    def test_runner_uses_comparator_and_accounts_each_direction(self):
        cases = adapter.validate()
        fixture = {"requests": cases["requests"][:1], "responses": [], "invalid": []}
        out = io.StringIO()
        with mock.patch.object(adapter, "validate", return_value=fixture), \
             mock.patch.object(adapter, "call", side_effect=[{"opcode": 0, "operands": []}, {"bytes": "01"}]), \
             contextlib.redirect_stdout(out):
            self.assertFalse(adapter.run("driver"))
        report = json.loads(out.getvalue().split("] ", 1)[1])
        self.assertEqual((report["cases"], report["assertions"], report["passed"], report["failed"]), (1, 2, 1, 1))
        self.assertEqual(report["outcomes"][1]["direction"], "encode")

    def test_legacy_scaling_and_comparison(self):
        self.assertEqual(legacy.control_arguments({"op": "setTargetResistance", "resistanceLevel": -1.2}),
                         ["encode-request", 4, -12])
        self.assertEqual(legacy.control_arguments({"op": "setWheelCircumference", "circumferenceMm": 2100}),
                         ["encode-request", 18, 21000])
        case = {"expectedBytes": [4, 244, 255]}
        self.assertTrue(legacy.compare_control_request(case, {"bytes": "04f4ff"})[0])
        self.assertFalse(legacy.compare_control_request(case, {"bytes": "04f400"})[0])

    def test_legacy_response_flags_drive_validated_view(self):
        malformed = {"expectedError": "malformed_response"}
        raw = {"requestOpcode": 21, "resultCode": 1, "parameter": 0, "low": 0, "high": 0,
               "unknownRequest": 1, "unknownResult": 0, "unexpectedParameters": 0}
        self.assertTrue(legacy.compare_control_response(malformed, raw)[0])
        raw["unknownRequest"] = 0
        self.assertFalse(legacy.compare_control_response(malformed, raw)[0])
        raw["unexpectedParameters"] = 1
        self.assertTrue(legacy.compare_control_response(malformed, raw)[0])


if __name__ == "__main__":
    unittest.main()
