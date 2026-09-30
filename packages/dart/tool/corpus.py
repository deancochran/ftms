"""Repository-only corpus validation/provenance, never a protocol oracle."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
SHARED = ROOT / "shared/conformance"
CONTRACTS = {
    "codec": ("v1/vectors.json", "v1/schema.json", "README.md"),
    "values": ("values/v1/vectors.json", "values/v1/schema.json", "values/README.md"),
    "controls": ("controls/v1/vectors.json", "controls/v1/schema.json", "controls/README.md"),
    "measurements": ("measurements/v1/vectors.json", "measurements/v1/schema.json", "measurements/README.md"),
    "statuses": ("statuses/v1/vectors.json", "statuses/v1/schema.json", "statuses/README.md"),
    "inspection": ("inspection/v1/fixtures.json", None, "inspection/v1/README.md"),
    "compatibility": ("compatibility/v1/vectors.json", "compatibility/v1/schema.json", "compatibility/README.md"),
    "capabilities": ("capabilities/v1/vectors.json", "capabilities/v1/schema.json", "capabilities/README.md"),
    "matrix": ("measurement-matrix/v1/layouts.json", None, "measurement-matrix/v1/README.md"),
}
CODEC_CATEGORIES = ("features", "ranges", "controls", "controlResponses", "measurements", "statuses", "diagnostics")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def provenance() -> dict:
    return {"sourceCommit": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--untracked-files=all"))}


def expand(templates: dict, spec: dict):
    """Expand literal templates only. Every path step is checked; no defaulting."""
    if spec["template"] not in templates:
        raise ValueError("Unknown template")
    root = copy.deepcopy(templates[spec["template"]])

    def edit(node, path, op, value):
        if not path:
            if op == "replace":
                return copy.deepcopy(value)
            if op == "append" and isinstance(node, list):
                node.append(copy.deepcopy(value))
                return node
            raise ValueError("Invalid root edit or append target")
        head, *tail = path
        if isinstance(node, list):
            if head == "*":
                keys = list(range(len(node)))
            elif isinstance(head, list):
                keys = head
                if len(set(keys)) != len(keys):
                    raise ValueError("Duplicate selection index")
            else:
                keys = [head]
            if (head == "*" or isinstance(head, list)) and op != "replace":
                raise ValueError("Selections only support replacement")
            if any(type(k) is not int or k < 0 or k >= len(node) for k in keys):
                raise ValueError("Nonexistent array index")
        elif isinstance(node, dict):
            if not isinstance(head, str) or head not in node:
                raise ValueError("Nonexistent object member")
            keys = [head]
        else:
            raise ValueError("Path traverses a scalar")
        for key in keys:
            if not tail and op == "remove":
                del node[key]
            else:
                node[key] = edit(node[key], tail, op, value)
        return node

    for change in spec.get("edits", []):
        op = change.get("op", "replace")
        if op not in ("replace", "append", "remove"):
            raise ValueError("Unknown edit operation")
        root = edit(root, change["path"], op, change.get("value"))
    return root


def cases(name: str, data: dict) -> list[dict]:
    if name == "codec":
        unknown = [k for k, v in data.items() if isinstance(v, list)
                   and k not in (*CODEC_CATEGORIES, "provenance", "errata")]
        if unknown:
            raise ValueError(f"Unhandled codec categories: {unknown}")
        return [dict(case, category=category) for category in CODEC_CATEGORIES for case in data[category]]
    if name in ("controls", "statuses"):
        categories = ("requests", "responses", "invalid") if name == "controls" else ("machine", "training")
        return [dict(case, category=category) for category in categories for case in data[category]]
    if name == "matrix":
        return []  # Generated layouts have their own executed-count evidence.
    return data["cases"]


def validate() -> dict:
    report = {**provenance(), "schemaValidator": "jsonschema Draft202012Validator", "corpora": {}}
    for name, (vectors, schema_path, contract) in CONTRACTS.items():
        data = json.loads((SHARED / vectors).read_text())
        files = [vectors, contract]
        if schema_path:
            files.append(schema_path)
            schema = json.loads((SHARED / schema_path).read_text())
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
            validator.validate(data)
            if name == "capabilities":
                for case in data["cases"]:
                    for side, templates, definition in (("input", "snapshots", "snapshot"), ("expected", "reports", "report")):
                        expanded = expand(data[templates], case[side])
                        validator.evolve(schema={"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}).validate(expanded)
        discovered = cases(name, data)
        ids = [case["id"] for case in discovered]
        if len(ids) != len(set(ids)) or (name != "matrix" and not ids):
            raise ValueError(f"{name}: empty corpus or duplicate case IDs")
        if name == "codec":
            if not schema["$id"].endswith("/v0.2.0/conformance/v1/schema.json"):
                raise ValueError("Historical schema identity changed")
            sources = {s["id"] for s in data["provenance"]}
            if not {"E8991", "E9135", "EC23224"}.issubset({s["id"] for s in data["errata"]}):
                raise ValueError("Required errata provenance missing")
            if any(not c["source"] or not set(c["source"]).issubset(sources) for c in discovered + data["errata"]):
                raise ValueError("Unresolved provenance")
        hashes = {str((SHARED / p).relative_to(ROOT)): sha256(SHARED / p) for p in files}
        if name == "capabilities":
            p = ROOT / "shared/protocol/capability-discovery.md"
            hashes[str(p.relative_to(ROOT))] = sha256(p)
        report["corpora"][name] = {
            "schemaVersion": data.get("schemaVersion"), "hashes": hashes,
            "schemaValidated": bool(schema_path),
            "caseIds": ids,
            "categories": {category: sum(c.get("category", "cases") == category for c in discovered)
                           for category in sorted({c.get("category", "cases") for c in discovered})},
        }
    return report


def generate_browser_data() -> None:
    """Disposable snapshot of exact canonical bytes, not a second fixture owner."""
    values = {"../../" + str(p.relative_to(ROOT)): p.read_text()
              for p in sorted(SHARED.rglob("*.json"))}
    encoded = json.dumps(values, ensure_ascii=True)
    # Encode the whole map once more as a Dart string, escaping interpolation.
    literal = json.dumps(encoded, ensure_ascii=True).replace("$", r"\$")
    target = PACKAGE / "test/support/corpus_browser.g.dart"
    target.write_text("// Generated from canonical shared files; do not edit.\n"
                      "import 'dart:convert';\n"
                      f"final _files = jsonDecode({literal}) as Map<String, dynamic>;\n"
                      "String readCorpus(String path) {\n"
                      "  final text = _files[path];\n"
                      "  if (text is! String) throw StateError('Unknown canonical file: $path');\n"
                      "  return text;\n}\n")


if __name__ == "__main__":
    report = validate()
    generate_browser_data()
    destination = PACKAGE / "build/schema-report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Validated {len(report['corpora'])} canonical corpus identities")
