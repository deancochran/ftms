import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "shared/conformance/inspection/v1/fixtures.json"
KINDS = {"speed": 0, "inclination": 1, "resistance": 2, "heartRate": 3, "power": 4}

class InspectionCorpus(unittest.TestCase):
    def test_all_synthetic_cases(self):
        driver_text = os.environ.get("FTMS_INSPECTION_DRIVER")
        self.assertIsNotNone(driver_text, "inspection driver must be supplied")
        driver = Path(driver_text)
        cases = json.loads(FIXTURES.read_text())["cases"]
        self.assertEqual(len(cases), 9)
        seen = set()
        for case in cases:
            self.assertNotIn(case["id"], seen); seen.add(case["id"])
            args = [str(driver), str(KINDS[case["kind"]]), bytes(case["bytes"]).hex()]
            if "options" in case:
                args.append(case["options"]["resistanceFormat"])
            actual = json.loads(subprocess.check_output(args, text=True))
            self.assertEqual(actual, case["expected"], case["id"])

if __name__ == "__main__":
    unittest.main()
