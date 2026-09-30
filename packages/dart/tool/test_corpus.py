import unittest

from corpus import expand


class ExpansionTests(unittest.TestCase):
    def test_independent_copy_and_order(self):
        template = {"t": {"rows": [{"x": 1}, {"x": 2}]}}
        result = expand(template, {"template": "t", "edits": [
            {"path": ["rows", "*", "x"], "value": 3},
            {"op": "remove", "path": ["rows", 0]},
            {"op": "append", "path": ["rows"], "value": {"x": 4}},
        ]})
        self.assertEqual(result, {"rows": [{"x": 3}, {"x": 4}]})
        self.assertEqual(template["t"]["rows"][0]["x"], 1)

    def test_invalid_paths_and_edits(self):
        for edit in [
            {"path": ["rows", "0"], "value": 1},
            {"path": ["rows", -1], "value": 1},
            {"path": ["rows", 1], "value": 1},
            {"path": ["rows", [0, 0]], "value": 1},
            {"path": ["absent"], "value": 1},
            {"path": [], "op": "remove"},
            {"path": ["rows", "*"], "op": "remove"},
            {"path": [], "op": "merge", "value": {}},
        ]:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                expand({"t": {"rows": [0]}}, {"template": "t", "edits": [edit]})


if __name__ == "__main__":
    unittest.main()
