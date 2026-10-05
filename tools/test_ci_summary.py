import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("ci_summary", Path(__file__).with_name("ci-summary.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def needs(selected="true"):
    jobs = {name: {"result": "success" if selected == "true" else "skipped"} for name in module.JOBS.values()}
    jobs.update({"changes": {"result": "success", "outputs": dict.fromkeys(module.JOBS, selected)},
                 "workflow-lint": {"result": "success"}})
    return jobs


class SummaryTests(unittest.TestCase):
    def test_all_pass(self):
        module.validate(needs())

    def test_unselected_skips_allowed(self):
        module.validate(needs("false"))

    def test_non_success_results_rejected(self):
        for result in ("failure", "cancelled", "abandoned", "timed_out", "neutral", "", None):
            with self.subTest(result=result), self.assertRaises(ValueError):
                value = needs()
                value["kotlin"]["result"] = result
                module.validate(value)

    def test_selected_skip_rejected(self):
        value = needs()
        value["kotlin"]["result"] = "skipped"
        with self.assertRaises(ValueError):
            module.validate(value)

    def test_mandatory_job_skip_rejected(self):
        for name in ("changes", "workflow-lint"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                value = needs("false")
                value[name]["result"] = "skipped"
                module.validate(value)

    def test_missing_selection_rejected(self):
        value = needs()
        del value["changes"]["outputs"]["kotlin"]
        with self.assertRaises(ValueError):
            module.validate(value)

    def test_missing_dependency_rejected(self):
        value = needs()
        del value["kotlin"]
        with self.assertRaises(ValueError):
            module.validate(value)
