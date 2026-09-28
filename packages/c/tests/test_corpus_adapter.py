import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus_adapter import compare_feature, compare_range


class CorpusAdapterComparisonTest(unittest.TestCase):
    def test_rejects_wrong_zero_feature_output(self):
        case = {"expectedTrue": ["averageSpeedSupported"]}
        self.assertFalse(compare_feature(case, ["ok", "0", "0"])[0])

    def test_rejects_swapped_feature_words(self):
        case = {"expectedTrue": ["speedTargetSettingSupported"]}
        self.assertFalse(compare_feature(case, ["ok", "1", "0"])[0])

    def test_rejects_wrong_range_divisor_and_unit(self):
        case = {"kind": "speed", "expected": {"min": 5, "max": 30, "increment": 0.5, "unit": "km/h"}}
        self.assertFalse(compare_range(case, ["ok", "speed", "500", "3000", "50", "10", "0"])[0])
        self.assertFalse(compare_range(case, ["ok", "speed", "500", "3000", "50", "100", "1"])[0])
        self.assertFalse(compare_range(case, ["ok", "speed", "500", "3000", "50", "0", "0"])[0])
        self.assertFalse(compare_range(case, ["ok", "power", "500", "3000", "50", "100", "0"])[0])

    def test_rejects_wrong_range_error(self):
        case = {"kind": "speed", "expectedError": "length"}
        self.assertFalse(compare_range(case, ["error", "4"])[0])


if __name__ == "__main__":
    unittest.main()
