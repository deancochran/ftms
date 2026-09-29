import copy
import json
import os
import subprocess
import unittest
from pathlib import Path

from . import simulation_adapter as adapter

DATA = json.loads((adapter.V / "scenarios.json").read_text())


class SimulationContract(unittest.TestCase):
    def test_literal_schema_and_semantics(self):
        self.assertEqual(adapter.validateCorpus(DATA), [])

    def test_invalid_shapes_and_references(self):
        for value in (None, [], 1, {"scenarios": None}):
            self.assertTrue(adapter.validateCorpus(value))
        for mutate in (
            lambda d: d["profiles"].append(copy.deepcopy(d["profiles"][0])),
            lambda d: d["scenarios"].append(copy.deepcopy(d["scenarios"][0])),
            lambda d: d["scenarios"][0].update(profile="absent"),
            lambda d: d["scenarios"][0]["steps"][0].update(bytes=[True]),
            lambda d: d["scenarios"][0]["steps"][0].update(unknown=True),
            lambda d: d["scenarios"][0]["steps"][0]["expected"]["raw"]["values"].pop(),
            lambda d: d.update(scenarios=[]),
            lambda d: d["scenarios"][0]["steps"].append({"at": 1, "type": "capabilities", "caseId": "absent"}),
        ):
            bad = copy.deepcopy(DATA)
            mutate(bad)
            self.assertTrue(adapter.validateCorpus(bad))

    def test_strict_comparator(self):
        self.assertTrue(adapter.strict_equal({"a": 1, "b": [2]}, {"b": [2], "a": 1}))
        for actual in ({"a": True}, {"a": 1, "b": 0}, {}, {"a": [1, 2]}):
            self.assertFalse(adapter.strict_equal(actual, {"a": 1}))
        self.assertFalse(adapter.strict_equal([True], [1]))

    def test_scheduler_orders_time_then_source_index(self):
        scenario = {"generation": 7, "steps": [
            {"type": "feed", "at": 2, "generation": 7, "bytes": [0]},
            {"type": "feed", "at": 1, "generation": 7, "bytes": [1]},
            {"type": "feed", "at": 1, "generation": 7, "bytes": [2]},
        ]}
        commands, indexes = adapter.bridge_commands(scenario, DATA["profiles"][0], 0xffffffff)
        self.assertEqual(commands[1:], ["feed 7 0 01", "feed 7 0 02", "feed 7 1 00"])
        self.assertEqual(indexes, {1: 1, 2: 2, 0: 3})

    @unittest.skipUnless(os.environ.get("FTMS_SIMULATION_DRIVER"), "run via make test for compiled bridge")
    def test_execution_and_mutation_accounting(self):
        driver = Path(os.environ["FTMS_SIMULATION_DRIVER"])
        report = adapter.runCorpus(driver, DATA)
        self.assertTrue(report["complete"], report)
        self.assertEqual(report, adapter.runCorpus(driver, DATA))
        bad = copy.deepcopy(DATA)
        bad["scenarios"][0]["steps"][0]["expected"]["raw"]["values"][0] += 1
        mutated = adapter.runCorpus(driver, bad)
        self.assertFalse(mutated["complete"])
        self.assertEqual(mutated["failed"], 1)
        self.assertEqual(mutated["steps"], report["steps"])
        self.assertEqual(mutated["trace"][0]["outcome"], "failed")
        self.assertNotEqual(report["inputSha256"], mutated["inputSha256"])
        failed = adapter.runCorpus(driver.with_name("nonexistent-driver"), DATA)
        self.assertFalse(failed["complete"])
        self.assertTrue(failed["runnerErrors"])
        self.assertEqual(failed["failed"], failed["total"])
        self.assertEqual(failed["steps"], report["steps"])
        for command in ("init 256 1 5 0 0\n", "init -1 1 5 0 0\n", "init 0 1 5 0 0 extra\n",
                        "init 0 1 5 0 0\nfeed 1 0 xyz\n", "init 0 1 5 0 0\nreset extra\n"):
            process = subprocess.run([driver], input=command, text=True, capture_output=True, timeout=10)
            self.assertNotEqual(process.returncode, 0)
