#!/usr/bin/env python3
"""Host-only bidirectional consumer for explicit compatibility layouts."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "shared/conformance/compatibility/v1"
CONTRACT = ROOT / "shared/conformance/compatibility/README.md"
WIRE = ROOT / "shared/protocol/wire-compatibility.md"


def exact(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(exact(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(exact(a, e) for a, e in zip(actual, expected))
    return actual == expected


def measurement_call(driver, *args):
    return json.loads(subprocess.check_output([str(driver), *map(str, args)], text=True, timeout=10))


def range_call(driver, *args):
    fields = subprocess.check_output([str(driver), *map(str, args)], text=True, timeout=10).split()
    if len(fields) != 7 or fields[0] != "ok":
        return {"error": fields[1] if len(fields) > 1 else "bridge"}
    return {"ok": True, "kind": fields[1], "minimum": int(fields[2]), "maximum": int(fields[3]),
            "increment": int(fields[4]), "scaleDivisor": int(fields[5]), "unit": int(fields[6])}


def value_call(driver, *args):
    fields = subprocess.check_output([str(driver), *map(str, args)], text=True, timeout=10).split()
    if len(fields) == 3 and fields[0] == "ok":
        if int(fields[2]) != len(bytes.fromhex(fields[1])):
            raise ValueError("encoded byte count mismatch")
        return {"bytes": fields[1]}
    return {"error": fields[1] if len(fields) > 1 else "bridge"}


def format_args(case):
    options = case["options"]
    if case["area"] == "measurement":
        return [int(options["resistanceFormat"] == "signed16Tenths"), int(options["treadmillPaceFormat"] == "uint8Legacy")]
    return [int(options["resistanceFormat"] == "signed16Tenths")]


def validate():
    import jsonschema
    schema = json.loads((CORPUS / "schema.json").read_text())
    vectors = json.loads((CORPUS / "vectors.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(vectors, schema)
    ids = [case["id"] for case in vectors["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate compatibility fixture ID")
    return vectors["cases"]


def run(measurements, ranges, values):
    outcomes, errors, cases = [], [], []
    try:
        cases = validate()
        for case in cases:
            raw = bytes(case["bytes"]).hex()
            if case["area"] == "measurement":
                options = format_args(case)
                actions = [
                    ("decode", measurements, ["decode", case["kind"], raw, *options], case["expected"]),
                    ("encode", measurements, ["encode", case["expected"]["kind"], case["expected"]["flags"], case["expected"]["present"], case["expected"]["unavailable"], *case["expected"]["values"], *options], {"bytes": raw}),
                ]
            else:
                options = format_args(case)
                expected = case["expected"]
                actions = [
                    ("decode", ranges, [case["kind"], raw, *options], {"ok": True, **expected}),
                    ("encode", values, ["range", case["kind"], expected["minimum"], expected["maximum"], expected["increment"], expected["scaleDivisor"], expected["unit"], *options], {"bytes": raw}),
                ]
            for direction, driver, args, expected in actions:
                item = {"id": case["id"], "direction": direction, "category": case["area"]}
                try:
                    actual = (measurement_call(driver, *args) if case["area"] == "measurement"
                              else range_call(driver, *args) if direction == "decode"
                              else value_call(driver, *args))
                    item["outcome"] = "passed" if exact(actual, expected) else "failed"
                    if item["outcome"] == "failed": item["reason"] = f"actual {actual!r} != expected {expected!r}"
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    item.update(outcome="failed", reason=str(exc))
                outcomes.append(item)
    except Exception as exc:
        errors.append(str(exc))
    passed = sum(item["outcome"] == "passed" for item in outcomes)
    report = {"schemaVersion": 1, "cases": len(cases), "assertions": len(outcomes), "passed": passed,
              "failed": len(outcomes) - passed, "unsupported": 0, "skipped": 0,
              "categories": {area: sum(c["area"] == area for c in cases) for area in ("measurement", "range")},
              "outcomes": outcomes, "runnerErrors": errors}
    try:
        report["sourceCommit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        report["sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (CORPUS / "schema.json", CORPUS / "vectors.json", CONTRACT, WIRE)}
    except Exception as exc:
        errors.append(str(exc))
    report["complete"] = len(outcomes) == 2 * len(cases) and not report["failed"] and not errors
    print("[C compatibility conformance] " + json.dumps(report, sort_keys=True))
    return report["complete"]


if __name__ == "__main__":
    sys.exit(0 if len(sys.argv) == 4 and run(*(Path(arg) for arg in sys.argv[1:])) else 1)
