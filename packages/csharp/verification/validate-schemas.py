"""Validate the pinned canonical fixtures; never resolve schema references remotely."""
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, validators
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[3]
report = []
for suite in ("v1", "values/v1", "controls/v1", "measurements/v1", "statuses/v1", "compatibility/v1", "capabilities/v1"):
    directory = ROOT / "shared/conformance" / suite
    schema_path, vectors_path = directory / "schema.json", directory / "vectors.json"
    schema = json.loads(schema_path.read_text())
    data = json.loads(vectors_path.read_text())
    validator = validators.validator_for(schema, default=Draft202012Validator)
    validator.check_schema(schema)
    registry = Registry().with_resource(schema.get("$id", "urn:ftms:local"), Resource.from_contents(schema))
    validator(schema, registry=registry).validate(data)
    report.append({"suite": suite, "schemaSha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
                   "vectorsSha256": hashlib.sha256(vectors_path.read_bytes()).hexdigest(), "passed": True})
output = ROOT / "packages/csharp/artifacts/schema-validation.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({"complete": True, "suites": report}, indent=2) + "\n")
print(f"Validated {len(report)} canonical schemas and fixture documents.")
