#!/usr/bin/env python3
"""Execute every canonical static-capability corpus case against the Python API."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, cast

import jsonschema

from deancochran_ftms import (
    C7Evidence,
    CapabilitySnapshot,
    CharacteristicEvidence,
    DiscoveryState,
    ReadReason,
    ReadState,
    ServiceScope,
    TruthValue,
    evaluate_capabilities,
)

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replace(root: Any, path: list[Any], value: Any) -> None:
    head, *tail = path
    if not tail:
        selected = range(len(root)) if head == "*" else head if isinstance(head, list) else [head]
        for key in selected:
            if isinstance(root, dict) and key not in root:
                raise ValueError("replace path does not exist")
            root[key] = copy.deepcopy(value)
        return
    selected = range(len(root)) if head == "*" else head if isinstance(head, list) else [head]
    for key in selected:
        _replace(root[key], tail, value)


def _edit(root: Any, edit: dict[str, Any]) -> Any:
    path = cast(list[Any], edit["path"])
    operation = edit.get("op", "replace")
    if operation == "replace":
        if not path:
            return copy.deepcopy(edit["value"])
        _replace(root, path, edit["value"])
    elif operation == "append":
        target = root
        for key in path:
            target = target[key]
        if not isinstance(target, list):
            raise ValueError("append target is not an array")
        target.append(copy.deepcopy(edit["value"]))
    elif operation == "remove":
        if not path:
            raise ValueError("cannot remove root")
        target = root
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]
    else:
        raise ValueError(f"unsupported edit: {operation}")
    return root


def _expand(source: dict[str, Any], templates: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(templates[source["template"]])
    for edit in source["edits"]:
        result = _edit(result, edit)
    return cast(dict[str, Any], result)


def _snapshot(value: dict[str, Any]) -> CapabilitySnapshot:
    c7 = value.get("c7")
    return CapabilitySnapshot(
        DiscoveryState(value["discovery"]),
        ServiceScope(value["scope"]),
        value["generation"],
        tuple(
            CharacteristicEvidence(
                c["uuid"],
                c["properties"],
                ReadState(c["readState"]),
                ReadReason(c["reason"]),
                bytes.fromhex(c["bytes"]),
            )
            for c in value["characteristics"]
        ),
        None
        if c7 is None
        else C7Evidence(
            TruthValue(c7["bondingSupported"]), TruthValue(c7["featureMayChangeOverLifetime"])
        ),
    )


def run(directory: Path | None = None) -> dict[str, Any]:
    corpus = directory or ROOT / "shared/conformance/capabilities/v1"
    schema_path, vectors_path = corpus / "schema.json", corpus / "vectors.json"
    contract_path, protocol_path = (
        corpus.parent / "README.md",
        ROOT / "shared/protocol/capability-discovery.md",
    )
    report: dict[str, Any] = {"runnerErrors": []}
    try:
        schema = json.loads(schema_path.read_text())
        vectors = json.loads(vectors_path.read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(vectors, schema)
        snapshot_validator = jsonschema.Draft202012Validator(
            {"$defs": schema["$defs"], "$ref": "#/$defs/snapshot"}
        )
        report_validator = jsonschema.Draft202012Validator(
            {"$defs": schema["$defs"], "$ref": "#/$defs/report"}
        )
        ids = [case["id"] for case in vectors["cases"]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate fixture IDs")
        outcomes = []
        for case in vectors["cases"]:
            try:
                expanded = _expand(case["input"], vectors["snapshots"])
                expected = _expand(case["expected"], vectors["reports"])
                snapshot_validator.validate(expanded)
                report_validator.validate(expected)
                actual = evaluate_capabilities(_snapshot(expanded)).to_wire()
                report_validator.validate(actual)
                matched = _exact(actual, expected)
                reason = "" if matched else "exact report mismatch"
            except Exception as error:
                matched = False
                reason = f"{type(error).__name__}: {error}"
                report["runnerErrors"].append({"id": case["id"], "reason": reason})
            outcomes.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "outcome": "passed" if matched else "failed",
                    "reason": reason,
                }
            )
        counts = {
            key: sum(item["outcome"] == key for item in outcomes)
            for key in ("passed", "failed", "unsupported", "skipped")
        }
        by_category = {
            category: sum(case["category"] == category for case in vectors["cases"])
            for category in sorted({case["category"] for case in vectors["cases"]})
        }
        report.update(
            {
                "sourceCommit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                "dirty": bool(
                    subprocess.check_output(
                        ["git", "status", "--porcelain"], cwd=ROOT, text=True
                    ).strip()
                ),
                "schemaVersion": vectors["schemaVersion"],
                "hashes": {
                    str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path): _sha(path)
                    for path in (schema_path, vectors_path, contract_path, protocol_path)
                },
                "caseCounts": {"total": len(outcomes), "byCategory": by_category},
                "assertionCounts": {"total": len(outcomes), **counts},
                "outcomes": outcomes,
                "complete": bool(outcomes)
                and not any(counts[key] for key in ("failed", "unsupported", "skipped")),
            }
        )
    except Exception as error:
        report["runnerErrors"].append({"reason": f"{type(error).__name__}: {error}"})
        report["complete"] = False
    return report


def _exact(actual: object, expected: object) -> bool:
    """JSON-type exact, including integer versus boolean and ordered arrays."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _exact(value, expected[key]) for key, value in actual.items()
        )
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact(a, e) for a, e in zip(actual, expected, strict=True)
        )
    return actual == expected


if __name__ == "__main__":
    result = run()
    (PACKAGE / "build").mkdir(exist_ok=True)
    (PACKAGE / "build/capability-verification-report.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["complete"] else 1)
