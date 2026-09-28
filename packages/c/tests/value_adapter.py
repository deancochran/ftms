#!/usr/bin/env python3
"""Exact host runner for canonical Feature/range encoder and decoder pairs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VALUES = ROOT / "shared/conformance/values/v1"


def invoke(driver, *args):
    return subprocess.check_output([str(driver), *map(str, args)], text=True, timeout=10).strip().split()


def validate():
    import jsonschema
    schema = json.loads((VALUES / "schema.json").read_text())
    vectors = json.loads((VALUES / "vectors.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(vectors, schema)
    ids = [case["id"] for case in vectors["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate value fixture ID")
    return vectors


def run(driver, decoder):
    outcomes, errors, cases = [], [], []
    try:
        cases = validate()["cases"]
        for case in cases:
            encoded = bytes(case["expectedBytes"]).hex()
            if case["operation"] == "features":
                args = ["features", case["machine"], case["target"]]
                decode_args = ["feature", encoded]
                decoded = ["ok", str(case["machine"]), str(case["target"])]
            else:
                args = ["range", case["kind"], case["minimum"], case["maximum"], case["increment"], case["scaleDivisor"], case["unit"]]
                decode_args = [case["kind"], encoded]
                decoded = ["ok", *map(str, args[1:])]
            for direction, executable, arguments, expected in [
                ("encode", driver, args, ["ok", encoded, str(len(case["expectedBytes"]))]),
                ("decode", decoder, decode_args, decoded),
            ]:
                item = {"id": case["id"], "direction": direction, "category": case["operation"]}
                try:
                    actual = invoke(executable, *arguments)
                    item["outcome"] = "passed" if actual == expected else "failed"
                    if item["outcome"] == "failed":
                        item["reason"] = f"actual {actual!r} != expected {expected!r}"
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    item.update(outcome="failed", reason=str(exc))
                outcomes.append(item)
    except Exception as exc:
        errors.append(str(exc))
    passed = sum(item["outcome"] == "passed" for item in outcomes)
    report = {"schemaVersion": 1, "cases": len(cases), "assertions": len(outcomes), "passed": passed,
              "failed": len(outcomes) - passed, "unsupported": 0, "skipped": 0,
              "categories": {kind: sum(c["operation"] == kind for c in cases) for kind in ("features", "range")},
              "outcomes": outcomes, "runnerErrors": errors}
    try:
        report["sourceCommit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        report["sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (VALUES / "schema.json", VALUES / "vectors.json", VALUES.parent / "README.md")}
    except Exception as exc:
        errors.append(str(exc))
    report["complete"] = bool(outcomes) and not report["failed"] and not errors and len(outcomes) == 2 * len(cases)
    print("[C value conformance] " + json.dumps(report, sort_keys=True))
    return report["complete"]


if __name__ == "__main__":
    sys.exit(0 if len(sys.argv) == 3 and run(Path(sys.argv[1]), Path(sys.argv[2])) else 1)
