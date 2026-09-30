"""Strict literal fixture expansion, not a capability reference implementation."""
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry


def selected(container, segment, op):
    if isinstance(container, dict):
        if not isinstance(segment, str) or segment not in container:
            raise ValueError("missing object key or wrong path segment type")
        return [segment]
    if not isinstance(container, list):
        raise ValueError("path traverses a scalar")
    if segment == "*":
        if op != "replace":
            raise ValueError("wildcard only supported for replacement")
        return list(range(len(container)))
    if isinstance(segment, list):
        if op != "replace" or not segment:
            raise ValueError("index selection only supported for replacement")
        indices = segment
    else:
        indices = [segment]
    if any(type(i) is not int or i < 0 or i >= len(container) for i in indices):
        raise ValueError("invalid array index")
    if len(set(indices)) != len(indices):
        raise ValueError("duplicate selection indices")
    return indices


def apply(value, path, op, replacement=None):
    if not path:
        if op == "replace":
            return copy.deepcopy(replacement)
        if op == "append" and isinstance(value, list):
            value.append(copy.deepcopy(replacement))
            return value
        raise ValueError("invalid root edit or append target")
    keys = selected(value, path[0], op)
    for key in keys:
        if len(path) == 1 and op == "remove":
            del value[key]
        else:
            value[key] = apply(value[key], path[1:], op, replacement)
    return value


def expand(templates, expansion):
    if expansion["template"] not in templates:
        raise ValueError("unknown template")
    value = copy.deepcopy(templates[expansion["template"]])
    for edit in expansion["edits"]:
        op = edit.get("op", "replace")
        if op not in ("replace", "append", "remove"):
            raise ValueError("unsupported edit")
        if (op != "remove") != ("value" in edit):
            raise ValueError("invalid edit value")
        value = apply(value, edit["path"], op, edit.get("value"))
    return value


def validate_cases(schema, vectors):
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, registry=Registry())
    validator.validate(vectors)
    validators = {kind: Draft202012Validator(
        {"$ref": f"#/$defs/{kind}", "$defs": schema["$defs"]}, registry=Registry())
        for kind in ("snapshot", "report")}
    ids = set()
    cases = []
    for case in vectors["cases"]:
        if case["id"] in ids:
            raise ValueError("duplicate case ID")
        ids.add(case["id"])
        snapshot = expand(vectors["snapshots"], case["input"])
        report = expand(vectors["reports"], case["expected"])
        validators["snapshot"].validate(snapshot)
        validators["report"].validate(report)
        cases.append({"id": case["id"], "category": case["category"],
                      "snapshot": snapshot, "expected": report})
    if not cases:
        raise ValueError("empty corpus")
    return cases


def load():
    if importlib.metadata.version("jsonschema") != "4.26.0":
        raise ValueError("install scripts/requirements.txt")
    shared = Path(__file__).resolve().parents[3] / "shared"
    paths = {"schema": shared / "conformance/capabilities/v1/schema.json",
             "vectors": shared / "conformance/capabilities/v1/vectors.json",
             "comparisonContract": shared / "conformance/capabilities/README.md",
             "protocolContract": shared / "protocol/capability-discovery.md"}
    data = {key: path.read_bytes() for key, path in paths.items()}
    schema = json.loads(data["schema"])
    vectors = json.loads(data["vectors"])
    cases = validate_cases(schema, vectors)
    return {"schemaVersion": vectors["schemaVersion"], "schemaID": schema["$id"],
            "schemaValidation": "passed", "specificationBasis": vectors["specificationBasis"],
            "hashes": {key: hashlib.sha256(value).hexdigest() for key, value in data.items()},
            "cases": cases}


if __name__ == "__main__":
    print(json.dumps(load()))
