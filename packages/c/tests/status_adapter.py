#!/usr/bin/env python3
"""Direct, exact bidirectional Machine and Training Status corpus consumer."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from control_adapter import exact

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "shared/conformance/statuses/v1"


def call(driver, *arguments):
    command = [str(driver), *map(str, arguments)]
    return json.loads(subprocess.check_output(command, text=True, timeout=10))


def validate():
    import jsonschema

    schema = json.loads((CORPUS / "schema.json").read_text())
    vectors = json.loads((CORPUS / "vectors.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(vectors, schema)
    cases = vectors["machine"] + vectors["training"]
    identifiers = [case["id"] for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate status fixture ID")
    return vectors


def encode_arguments(case):
    decoded = case["decoded"]
    if case["operation"] == "training":
        return ["encode-training", decoded["flags"], decoded["code"], decoded["textHex"]]
    parameter = decoded["parameter"]
    operands = parameter["operands"] if parameter is not None else []
    tag = parameter["opcode"] if parameter is not None else -1
    return ["encode-machine", decoded["opcode"], tag, decoded["action"], *operands]


def run(driver):
    errors = []
    outcomes = []
    counts = {"machine": 0, "training": 0}
    try:
        vectors = validate()
        cases = vectors["machine"] + vectors["training"]
        counts = {category: len(vectors[category]) for category in counts}
        for case in cases:
            actions = [("decode", ["decode-" + case["operation"], bytes(case["bytes"]).hex()],
                        case["decoded"])]
            if case["encode"]:
                actions.append(("encode", encode_arguments(case),
                                {"bytes": bytes(case["bytes"]).hex()}))
            for direction, arguments, expected in actions:
                item = {"id": case["id"], "category": case["operation"], "direction": direction}
                try:
                    actual = call(driver, *arguments)
                    item["outcome"] = "passed" if exact(actual, expected) else "failed"
                    if item["outcome"] == "failed":
                        item["reason"] = f"actual {actual!r} != expected {expected!r}"
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    item.update(outcome="failed", reason=str(exc))
                outcomes.append(item)
    except Exception as exc:
        errors.append(str(exc))

    passed = sum(item["outcome"] == "passed" for item in outcomes)
    report = {
        "schemaVersion": 1,
        "cases": sum(counts.values()),
        "categories": counts,
        "outcomes": outcomes,
        "assertions": len(outcomes),
        "passed": passed,
        "failed": len(outcomes) - passed,
        "unsupported": 0,
        "skipped": 0,
        "runnerErrors": errors,
    }
    try:
        report["sourceCommit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["dirty"] = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        report["sha256"] = {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (CORPUS / "schema.json", CORPUS / "vectors.json", CORPUS.parent / "README.md")
        }
    except Exception as exc:
        errors.append(str(exc))
    report["complete"] = bool(outcomes) and not report["failed"] and not errors
    print("[C status conformance] " + json.dumps(report, sort_keys=True))
    return report["complete"]


if __name__ == "__main__":
    sys.exit(0 if len(sys.argv) == 2 and run(Path(sys.argv[1])) else 1)
