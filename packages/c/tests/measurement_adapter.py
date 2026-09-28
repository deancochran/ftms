#!/usr/bin/env python3
"""Exact host-only consumer for the raw C measurement corpus."""
import hashlib, json, subprocess, sys
from pathlib import Path
from control_adapter import exact

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "shared/conformance/measurements/v1"


def call(driver, *args):
    return json.loads(subprocess.check_output([str(driver), *map(str, args)], text=True, timeout=10))


def validate():
    import jsonschema
    schema = json.loads((CORPUS / "schema.json").read_text())
    vectors = json.loads((CORPUS / "vectors.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(vectors, schema)
    ids = [case["id"] for case in vectors["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate measurement fixture ID")
    return vectors


def encode_args(case):
    item = case["decoded"]
    return ["encode", item["kind"], item["flags"], item["present"], item["unavailable"], *item["values"]]


def run(driver):
    outcomes, errors = [], []
    try:
        vectors = validate()
        for case in vectors["cases"]:
            actions = [("decode", ["decode", case["kind"], bytes(case["bytes"]).hex()], case["decoded"])]
            if case["encode"]:
                actions.append(("encode", encode_args(case), {"bytes": bytes(case["bytes"]).hex()}))
            for direction, args, expected in actions:
                outcome = {"id": case["id"], "direction": direction}
                try:
                    actual = call(driver, *args)
                    outcome["outcome"] = "passed" if exact(actual, expected) else "failed"
                    if outcome["outcome"] == "failed": outcome["reason"] = f"actual {actual!r} != expected {expected!r}"
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    outcome.update(outcome="failed", reason=str(exc))
                outcomes.append(outcome)
    except Exception as exc:
        errors.append(str(exc))
        vectors = {"cases": []}
    passed = sum(x["outcome"] == "passed" for x in outcomes)
    report = {"schemaVersion": 1, "cases": len(vectors["cases"]), "assertions": len(outcomes),
              "passed": passed, "failed": len(outcomes) - passed, "unsupported": 0, "skipped": 0,
              "outcomes": outcomes, "runnerErrors": errors}
    try:
        report["sourceCommit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        report["sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (CORPUS / "schema.json", CORPUS / "vectors.json", CORPUS.parent / "README.md")}
    except Exception as exc:
        errors.append(str(exc))
    report["complete"] = bool(outcomes) and not report["failed"] and not errors
    print("[C measurement conformance] " + json.dumps(report, sort_keys=True))
    return report["complete"]

if __name__ == "__main__":
    sys.exit(0 if len(sys.argv) == 2 and run(Path(sys.argv[1])) else 1)
