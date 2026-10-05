import unittest

from check_instrumentation import CLASS, TESTS, validate


def event(name, code):
    return (f"INSTRUMENTATION_STATUS: class={CLASS}\n"
            f"INSTRUMENTATION_STATUS: numtests=4\n"
            f"INSTRUMENTATION_STATUS: test={name}\n"
            f"INSTRUMENTATION_STATUS_CODE: {code}\n")


def success():
    return "".join(event(name, 1) + event(name, 0) for name in sorted(TESTS)) + "OK (4 tests)\nINSTRUMENTATION_CODE: -1\n"


class InstrumentationAccountingTest(unittest.TestCase):
    def test_success(self):
        validate(success())

    def test_crlf_success(self):
        validate(success().replace("\n", "\r\n"))

    def test_reject_empty(self):
        with self.assertRaises(ValueError):
            validate("")

    def test_reject_summary_without_tests(self):
        with self.assertRaises(ValueError):
            validate("OK (4 tests)\nINSTRUMENTATION_CODE: -1\n")

    def test_reject_failure_skip_and_assumption(self):
        for code in [-1, -2, -3, -4]:
            with self.subTest(code=code), self.assertRaises(ValueError):
                validate(success().replace("INSTRUMENTATION_STATUS_CODE: 0", f"INSTRUMENTATION_STATUS_CODE: {code}", 1))

    def test_reject_missing_test(self):
        name = sorted(TESTS)[0]
        with self.assertRaises(ValueError):
            validate(success().replace(event(name, 1) + event(name, 0), ""))

    def test_reject_duplicate_test(self):
        name = sorted(TESTS)[0]
        with self.assertRaises(ValueError):
            validate(event(name, 1) + event(name, 0) + success())

    def test_reject_unknown_test_or_class(self):
        for old in [sorted(TESTS)[0], CLASS]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                validate(success().replace(old, "unexpected"))

    def test_reject_missing_start(self):
        with self.assertRaises(ValueError):
            validate(success().replace(event(sorted(TESTS)[0], 1), ""))

    def test_reject_runner_failure(self):
        with self.assertRaises(ValueError):
            validate(success() + "INSTRUMENTATION_FAILED: process crashed\n")

    def test_reject_wrong_count_or_final_code(self):
        for old, new in [("numtests=4", "numtests=3"), ("CODE: -1", "CODE: 0"), ("OK (4 tests)", "OK (0 tests)")]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                validate(success().replace(old, new))


if __name__ == "__main__":
    unittest.main()
