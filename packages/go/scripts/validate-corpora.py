"""Validate the exact canonical schemas before Go conformance execution."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry

if importlib.metadata.version("jsonschema") != "4.26.0":
    raise SystemExit("Install packages/go/scripts/requirements.txt in a contributor venv")

root = Path(__file__).resolve().parents[3] / "shared" / "conformance"
reports = []
for name in ("values", "controls", "measurements", "statuses", "compatibility"):
    directory = root / name
    schema_path = directory / "v1/schema.json"
    vectors_path = directory / "v1/vectors.json"
    schema = json.loads(schema_path.read_bytes())
    vectors = json.loads(vectors_path.read_bytes())
    Draft202012Validator.check_schema(schema)
    # No network retrieval for references in untrusted fixture/schema text.
    Draft202012Validator(schema, registry=Registry()).validate(vectors)
    ids = []
    for value in vectors.values():
        if isinstance(value, list):
            ids.extend(case["id"] for case in value if isinstance(case, dict) and "id" in case)
    if not ids or len(ids) != len(set(ids)):
        raise SystemExit(f"{name}: missing cases or duplicate IDs")
    reports.append({
        "corpus": f"{name}/v1", "schemaVersion": vectors["schemaVersion"],
        "schemaValidation": "passed", "cases": len(ids),
        "hashes": {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (schema_path, vectors_path, directory / "README.md")},
    })
print(json.dumps(reports, indent=2))
