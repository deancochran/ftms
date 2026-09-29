#!/usr/bin/env python3
"""Exact, host-only capability corpus runner; no production dependencies."""
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "shared/conformance/capabilities/v1"


def expand(spec, templates):
    """Expand literal templates with deterministic edits, never inferred rules.

    Paths address existing keys/indices. A list of indices (or '*') selects list
    members. Only replacement permits multiple selections. Appends/removes are
    single-location operations. Each edit acts on the preceding edit's result.
    """
    result = copy.deepcopy(templates[spec["template"]])
    for edit in spec["edits"]:
        operation = edit.get("op", "replace")
        nodes = [(None, None, result)]
        for segment in edit["path"]:
            next_nodes = []
            for _, _, node in nodes:
                if segment == "*" or isinstance(segment, list):
                    if not isinstance(node, list) or operation != "replace":
                        raise ValueError("selection requires an array replacement")
                    keys = list(range(len(node))) if segment == "*" else segment
                    if len(keys) != len(set(keys)):
                        raise ValueError("duplicate selection index")
                else:
                    keys = [segment]
                for key in keys:
                    if isinstance(node, list):
                        if type(key) is not int or not 0 <= key < len(node):
                            raise ValueError("invalid array edit index")
                    elif not isinstance(node, dict) or key not in node:
                        raise ValueError("edit must reference an existing field")
                    next_nodes.append((node, key, node[key]))
            nodes = next_nodes
        for parent, key, node in nodes:
            if operation == "replace":
                if parent is None:
                    result = copy.deepcopy(edit["value"])
                else:
                    parent[key] = copy.deepcopy(edit["value"])
            elif operation == "append":
                if not isinstance(node, list):
                    raise ValueError("append requires an array")
                node.append(copy.deepcopy(edit["value"]))
            elif operation == "remove":
                if parent is None:
                    raise ValueError("cannot remove root")
                del parent[key]
            else:
                raise ValueError("unknown edit operation")
    return result


def load_cases(corpus=CORPUS):
    schema = json.loads((corpus / "schema.json").read_text())
    vectors = json.loads((corpus / "vectors.json").read_text())
    return validate_vectors(vectors, schema)


def validate_vectors(vectors, schema):
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(vectors, schema)
    ids = [case["id"] for case in vectors["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate capability fixture ID")
    cases = []
    for case in vectors["cases"]:
        item = {"id": case["id"], "category": case["category"]}
        for field, group, definition in [("input", "snapshots", "snapshot"), ("expected", "reports", "report")]:
            item[field] = expand(case[field], vectors[group])
            jsonschema.validate(item[field], {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]})
        cases.append(item)
    return cases


def line(snapshot):
    c7 = snapshot.get("c7", {"bondingSupported": 0, "featureMayChangeOverLifetime": 0})
    rows = [f'{snapshot["discovery"]} {snapshot["scope"]} {snapshot["generation"]} {len(snapshot["characteristics"])} {c7["bondingSupported"]} {c7["featureMayChangeOverLifetime"]}']
    for c in snapshot["characteristics"]:
        rows.append(f'{c["uuid"]} {c["properties"]} {c["readState"]} {c["reason"]} {c["bytes"] or "-"}')
    return "\n".join(rows) + "\n"


def compare(actual, expected, path="$"):
    # Python considers True == 1; the corpus requires exact JSON types too.
    if type(actual) is not type(expected):
        return f"{path}: type mismatch"
    if isinstance(expected, dict):
        if actual.keys() != expected.keys():
            return f"{path}: object keys differ"
        for key in expected:
            error = compare(actual[key], expected[key], f"{path}.{key}")
            if error:
                return error
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            return f"{path}: array lengths differ"
        for index, (left, right) in enumerate(zip(actual, expected)):
            error = compare(left, right, f"{path}[{index}]")
            if error:
                return error
    elif actual != expected:
        return f"{path}: {actual!r} != {expected!r}"
    return None


def execute_case(driver, case):
    run = subprocess.run([driver], input=line(case["input"]), text=True, capture_output=True, timeout=10)
    if run.returncode:
        return f"driver exit {run.returncode}: {run.stderr.strip()}"
    return compare(json.loads(run.stdout), case["expected"])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv):
    if len(argv) != 2:
        return 64
    cases, failures, errors, outcomes = [], [], [], []
    try:
        cases = load_cases()
        for case in cases:
            try:
                reason = execute_case(argv[1], case)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                reason = str(exc)
            if reason:
                failures.append({"id": case["id"], "reason": reason})
            outcomes.append({"id": case["id"], "category": case["category"],
                             "outcome": "failed" if reason else "passed"})
    except Exception as exc:
        errors.append(str(exc))
    report = {
        "schemaVersion": 1, "total": len(cases),
        "passed": sum(item["outcome"] == "passed" for item in outcomes),
        "failed": len(failures), "unsupported": 0, "skipped": 0,
        "categories": dict(Counter(case["category"] for case in cases)),
        "outcomes": outcomes, "failures": failures, "runnerErrors": errors,
        "complete": bool(cases) and len(outcomes) == len(cases) and not failures and not errors,
    }
    try:
        report["sourceCommit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        report["sha256"] = {str(p.relative_to(ROOT)): sha256(p) for p in [
            CORPUS / "schema.json", CORPUS / "vectors.json", CORPUS.parent / "README.md",
            ROOT / "shared/protocol/capability-discovery.md",
        ]}
    except Exception as exc:
        errors.append(str(exc))
        report["complete"] = False
    print("[C capability conformance] " + json.dumps(report, sort_keys=True))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
