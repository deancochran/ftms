#!/usr/bin/env python3
"""Direct, exact bidirectional control corpus consumer (host tooling only)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "shared/conformance/controls/v1"
ERR = {"kind": 3, "length": 2, "range": 4}


def exact(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(exact(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(exact(a, b) for a, b in zip(actual, expected))
    return actual == expected


def call(driver, *args):
    return json.loads(subprocess.check_output([str(driver), *map(str, args)], text=True, timeout=10))


def validate():
    import jsonschema
    schema = json.loads((CORPUS / "schema.json").read_text())
    vectors = json.loads((CORPUS / "vectors.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(vectors, schema)
    ids = [case["id"] for category in ("requests", "responses", "invalid") for case in vectors[category]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate control fixture ID")
    return vectors


def run(driver):
    outcomes, errors, counts = [], [], {}
    try:
        vectors = validate()
        counts = {category: len(vectors[category]) for category in ("requests", "responses", "invalid")}
        for category in counts:
            for case in vectors[category]:
                actions = [("decode", ["decode-" + case["operation"], bytes(case["bytes"]).hex()],
                            {"error": ERR[case["error"]]} if category == "invalid" else case["decoded"])]
                if category != "invalid" and case.get("encode", True):
                    value = case["decoded"]
                    args = (["encode-request", value["opcode"], *value["operands"]] if case["operation"] == "request"
                            else ["encode-response", value["requestOpcode"], value["resultCode"], value["parameter"], value["low"], value["high"]])
                    actions.append(("encode", args, {"bytes": bytes(case["bytes"]).hex()}))
                for direction, args, expected in actions:
                    item = {"id": case["id"], "direction": direction, "category": category}
                    try:
                        actual = call(driver, *args)
                        item["outcome"] = "passed" if exact(actual, expected) else "failed"
                        if item["outcome"] == "failed":
                            item["reason"] = f"actual {actual!r} != expected {expected!r}"
                    except (OSError, ValueError, subprocess.SubprocessError) as exc:
                        item.update(outcome="failed", reason=str(exc))
                    outcomes.append(item)
    except Exception as exc:
        errors.append(str(exc))
    passed = sum(item["outcome"] == "passed" for item in outcomes)
    report = {"schemaVersion": 1, "cases": sum(counts.values()), "categories": counts,
              "outcomes": outcomes, "assertions": len(outcomes), "passed": passed,
              "failed": len(outcomes) - passed, "unsupported": 0, "skipped": 0, "runnerErrors": errors}
    try:
        report["sourceCommit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        report["sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (CORPUS / "schema.json", CORPUS / "vectors.json", CORPUS.parent / "README.md")}
    except Exception as exc:
        errors.append(str(exc))
    report["complete"] = bool(outcomes) and not report["failed"] and not errors
    print("[C control conformance] " + json.dumps(report, sort_keys=True))
    return report["complete"]


if __name__ == "__main__":
    sys.exit(0 if len(sys.argv) == 2 and run(Path(sys.argv[1])) else 1)
