#!/usr/bin/env python3
"""Fail closed on partial, skipped, duplicated or failed Android test runs."""
import re
import sys
from pathlib import Path

CLASS = "io.github.deancochran.ftms.example.telemetry.PublicArtifactInstrumentationTest"
TESTS = {
    "publicMavenArtifactDecodesOnAndroid",
    "demoRunsWithoutBluetoothAndDisconnectClearsIt",
    "stopAndResumeNeverRestoresStaleValues",
    "missingAndEmptyPermissionResultsDoNotStartScanning",
}


def validate(text):
    fields = {}
    started, passed = set(), set()
    for line in text.splitlines():
        field = re.fullmatch(r"INSTRUMENTATION_STATUS: (class|test|numtests)=(.*)", line)
        if field:
            fields[field[1]] = field[2]
        code = re.fullmatch(r"INSTRUMENTATION_STATUS_CODE: (-?\d+)", line)
        if not code:
            continue
        name = fields.get("test")
        if (fields.get("class") != CLASS or fields.get("numtests") != str(len(TESTS))
                or name not in TESTS or code[1] not in {"0", "1"}):
            raise ValueError("Unexpected, failed or skipped instrumentation test")
        if code[1] == "1":
            if name in started:
                raise ValueError("Duplicate test start")
            started.add(name)
        else:
            if name not in started or name in passed:
                raise ValueError("Missing start or duplicate completion")
            passed.add(name)
        fields = {}
    if (started != TESTS or passed != TESTS
            or re.findall(r"^INSTRUMENTATION_CODE: (-?\d+)\s*$", text, re.M) != ["-1"]
            or not re.search(r"^OK \(4 tests\)\s*$", text, re.M)
            or "INSTRUMENTATION_FAILED" in text):
        raise ValueError("Incomplete or failed Android runtime verification")


if __name__ == "__main__":
    try:
        validate(Path(sys.argv[1]).read_text())
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print("Verified: 4 named Android tests passed, zero failures/skips; no BLE access requested.")
