import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from control_adapter import exact
import corpus_adapter
import status_adapter as adapter


class StatusAdapterTest(unittest.TestCase):
    def status_case(self, identifier):
        vectors = adapter.validate()
        return next(case for category in ("machine", "training") for case in vectors[category]
                    if case["id"] == identifier)

    def assert_decode_mutation_rejected(self, identifier, mutate):
        case = self.status_case(identifier)
        actual = copy.deepcopy(case["decoded"])
        mutate(actual)
        self.assertFalse(exact(actual, case["decoded"]))
        vectors = {"machine": [case] if case["operation"] == "machine" else [],
                   "training": [case] if case["operation"] == "training" else []}
        responses = [actual]
        if case["encode"]:
            responses.append({"bytes": bytes(case["bytes"]).hex()})
        output = io.StringIO()
        with mock.patch.object(adapter, "validate", return_value=vectors), \
             mock.patch.object(adapter, "call", side_effect=responses), \
             contextlib.redirect_stdout(output):
            self.assertFalse(adapter.run("driver"))
        report = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual(report["outcomes"][0]["direction"], "decode")
        self.assertEqual(report["outcomes"][0]["outcome"], "failed")

    def test_runner_rejects_wrong_status_code(self):
        self.assert_decode_mutation_rejected("machine-opcode-05", lambda raw: raw.update(opcode=6))

    def test_runner_rejects_wrong_speed_operand(self):
        self.assert_decode_mutation_rejected(
            "machine-opcode-05", lambda raw: raw["parameter"]["operands"].__setitem__(0, 1235))

    def test_runner_rejects_wrong_simulation_raw_field(self):
        self.assert_decode_mutation_rejected(
            "machine-opcode-12", lambda raw: raw["parameter"]["operands"].__setitem__(2, 11))

    def test_runner_rejects_wrong_machine_diagnostic(self):
        self.assert_decode_mutation_rejected("machine-trailing", lambda raw: raw.update(trailingBytes=0))

    def test_runner_rejects_wrong_truncation(self):
        self.assert_decode_mutation_rejected("machine-short", lambda raw: raw.update(truncated=0))

    def test_runner_rejects_wrong_training_text_flag(self):
        self.assert_decode_mutation_rejected("training-valid-1", lambda raw: raw.update(textPresent=0))

    def legacy_case(self, identifier):
        vectors = json.loads((adapter.ROOT / "shared/conformance/v1/vectors.json").read_text())
        return next(case for case in vectors["statuses"] + vectors["diagnostics"]
                    if case["id"] == identifier)

    def native_raw(self, identifier):
        status_id = {
            "status-training-string": "training-valid-1",
            "status-machine-speed": "machine-opcode-05",
            "status-machine-simulation": "machine-opcode-12",
            "status-machine-permission-lost": "machine-opcode-ff",
            "diagnostic-machine-empty": "machine-empty",
        }[identifier]
        return copy.deepcopy(self.status_case(status_id)["decoded"])

    def test_legacy_projection_rejects_actual_raw_speed_operand(self):
        case = self.legacy_case("status-machine-speed")
        raw = self.native_raw("status-machine-speed")
        raw["parameter"]["operands"][0] = 1235
        self.assertFalse(corpus_adapter.compare_status_output(case, raw)[0])

    def test_legacy_projection_rejects_training_wrong_flags(self):
        case = self.legacy_case("status-training-string")
        raw = self.native_raw("status-training-string")
        raw["flags"] = 3
        self.assertFalse(corpus_adapter.compare_status_output(case, raw)[0])

    def test_legacy_projection_rejects_truncated_diagnostic(self):
        case = self.legacy_case("diagnostic-machine-empty")
        raw = self.native_raw("diagnostic-machine-empty")
        raw["truncated"] = 0
        self.assertFalse(corpus_adapter.compare_status_output(case, raw)[0])


if __name__ == "__main__":
    unittest.main()
