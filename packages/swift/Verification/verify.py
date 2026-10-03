#!/usr/bin/env python3
"""Host verification for the Swift package; no fixture copies or test stubs."""
import hashlib
import argparse
import importlib.metadata
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SWIFT = ROOT / "packages" / "swift"
REPORT_PATH = ROOT / ".build" / "swift-verification-report.json"
MARKER = "FTMS_NATIVE_CASE "


def run(command, *, cwd=ROOT):
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_schemas():
    try:
        import jsonschema
    except ImportError as error:
        raise RuntimeError("jsonschema is required for Swift verification; install it in the test environment") from error
    pairs = []
    for schema_path in sorted((ROOT / "shared").glob("**/schema.json")):
        candidates = [p for p in sorted(schema_path.parent.glob("*.json")) if p.name != "schema.json"]
        if not candidates:
            raise RuntimeError(f"schema has no JSON instance to validate: {schema_path.relative_to(ROOT)}")
        schema = json.loads(schema_path.read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        for instance_path in candidates:
            validator.validate(json.loads(instance_path.read_text()))
            pairs.append((schema_path.relative_to(ROOT), instance_path.relative_to(ROOT)))
    return pairs, importlib.metadata.version("jsonschema")


def git_state():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    return head, dirty


def matrix_accounting():
    path = ROOT / "shared/conformance/measurement-matrix/v1/layouts.json"
    contract = json.loads(path.read_text())
    if contract.get("contract") != "ftms-measurement-matrix-v1" or contract.get("columns") != ["flagBit", "width", "rawFieldIndex", "signed", "unavailableSentinel"]:
        raise RuntimeError("invalid measurement-matrix contract declaration")
    structural = sentinels = reserved = prefixes = 0
    for layout in contract["layouts"]:
        variants = 2 if layout["kind"] in (0, 1, 4, 5) else 1
        for variant in range(variants):
            structural += (1 << layout["optionalGroups"]) * 2 * (2 if layout["kind"] == 1 else 1)
            sentinels += sum(field[4] for field in layout["fields"])
            reserved += layout["flagBytes"] * 8 - (16 if layout["kind"] == 1 else layout["optionalGroups"] + 1)
            prefixes += layout["fullLength"] + (-2 if variant and layout["kind"] == 0 else 1 if variant else 0)
    accounting = {"structural": structural, "sentinels": sentinels, "reserved": reserved, "incompletePrefixes": prefixes}
    if (structural, sentinels, reserved) != (181_760, 46, 47):
        raise RuntimeError(f"unexpected measurement-matrix accounting: {accounting}")
    return accounting


def verify_local_consumer():
    with tempfile.TemporaryDirectory(prefix="ftms-swift-consumer-", dir=ROOT / ".build") as temporary:
        directory = Path(temporary)
        (directory / "Package.swift").write_text(f'''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "Consumer", platforms: [.macOS(.v13)], dependencies: [.package(path: "{ROOT}")], targets: [.executableTarget(name: "Consumer", dependencies: [.product(name: "FTMS", package: "{ROOT.name}")])])
''')
        (directory / "Sources" / "Consumer").mkdir(parents=True)
        (directory / "Sources" / "Consumer" / "main.swift").write_text('''import FTMS
let source = Measurement(kind: .treadmill, flags: 0, values: [.speed: 100])
let wire = try encodeMeasurement(source)
let decoded = try decodeMeasurement(.treadmill, bytes: wire)
precondition(decoded.values[.speed] == 100)
let universal = try decodeMeasurement(uuid: "00002acd-0000-1000-8000-00805f9b34fb", bytes: wire, format: .init())
guard case .measurement(let measurement) = universal else { fatalError("measurement UUID unsupported") }
precondition(measurement.metrics.speedMps == 100.0 / 360)
precondition(measurement.raw.format == .init())
''')
        run(["swift", "run", "Consumer"], cwd=directory)


def discovered_cases():
    groups = [
        ("codec-v1", ROOT / "shared/conformance/v1/vectors.json", ["features", "ranges", "controls", "controlResponses", "measurements", "statuses", "diagnostics"]),
        ("capabilities-v1", ROOT / "shared/conformance/capabilities/v1/vectors.json", ["cases"]),
        ("controls-v1", ROOT / "shared/conformance/controls/v1/vectors.json", ["requests", "responses", "invalid"]),
        ("statuses-v1", ROOT / "shared/conformance/statuses/v1/vectors.json", ["machine", "training"]),
        ("values-v1", ROOT / "shared/conformance/values/v1/vectors.json", ["cases"]),
        ("measurements-v1", ROOT / "shared/conformance/measurements/v1/vectors.json", ["cases"]),
        ("inspection-v1", ROOT / "shared/conformance/inspection/v1/fixtures.json", ["cases"]),
    ]
    cases = []
    for corpus, path, categories in groups:
        data = json.loads(path.read_text())
        for source_category in categories:
            for item in data[source_category]:
                # Capability fixtures declare their own meaningful category.
                category = item["category"] if corpus == "capabilities-v1" else source_category
                cases.append({"corpus": corpus, "category": category, "id": item["id"], "outcome": "not-run"})
    if len({(c["corpus"], c["id"]) for c in cases}) != len(cases):
        raise RuntimeError("duplicate corpus case identity in verifier discovery")
    return cases


def parse_markers(output):
    markers, errors = [], []
    for line in output.splitlines():
        if MARKER not in line:
            continue
        payload = line.split(MARKER, 1)[1]
        try:
            marker = json.loads(payload)
            if not all(isinstance(marker.get(key), str) for key in ("corpus", "category", "id")) or not all(isinstance(marker.get(key), int) and marker[key] > 0 for key in ("assertions", "directions")):
                raise ValueError("missing identity or positive assertion directions")
            markers.append(marker)
        except (json.JSONDecodeError, ValueError) as error:
            errors.append(f"invalid native case marker: {error}: {payload}")
    return markers, errors


def totals(cases):
    result = {"discovered": len(cases), "passed": 0, "failed": 0, "unsupported": 0, "skipped": 0, "unresolved": 0}
    for case in cases:
        if case["outcome"] in result:
            result[case["outcome"]] += 1
    return result


def write_report(report):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-clean", action="store_true", help="reject dirty CI/release checkouts")
    options = parser.parse_args()
    cases = discovered_cases()
    report = {"nativeCaseReport": {"cases": cases}}
    try:
        pairs, validator = validate_schemas()
        matrix = matrix_accounting()
        head, dirty = git_state()
        consumed = sorted(set((ROOT / "shared/conformance").glob("**/README.md")) | {ROOT / "shared/protocol/capability-discovery.md", ROOT / "shared/protocol/wire-compatibility.md"})
        consumed += sorted({ROOT / schema for schema, _ in pairs} | {ROOT / instance for _, instance in pairs})
        report.update({"gitHead": head, "sourceDirty": dirty, "jsonSchemaValidator": validator,
                       "toolchain": subprocess.check_output(["swift", "--version"], text=True).strip(),
                       "platform": platform.platform(),
                       "validatedSchemaInstances": [{"schema": str(s), "instance": str(i)} for s, i in pairs],
                       "sha256": {str(path.relative_to(ROOT)): digest(path) for path in consumed},
                       "measurementMatrix": matrix})
        if options.require_clean and dirty:
            raise RuntimeError("CI/release verification requires a clean checkout")

        print("+ swift test", flush=True)
        test = subprocess.run(["swift", "test"], cwd=ROOT, text=True, capture_output=True)
        sys.stdout.write(test.stdout)
        sys.stderr.write(test.stderr)
        markers, marker_errors = parse_markers(test.stdout + "\n" + test.stderr)
        expected = {(c["corpus"], c["category"], c["id"]): c for c in cases}
        seen = set()
        for marker in markers:
            identity = (marker["corpus"], marker["category"], marker["id"])
            if identity not in expected:
                marker_errors.append(f"marker is not a discovered case: {identity}")
            elif identity in seen:
                marker_errors.append(f"duplicate marker: {identity}")
            else:
                seen.add(identity)
                expected[identity]["assertions"] = marker["assertions"]
                expected[identity]["directions"] = marker["directions"]

        if test.returncode != 0:
            report["runnerError"] = f"swift test exited {test.returncode}"
            for case in cases:
                case["outcome"] = "unresolved"
                case["reason"] = "test process failed; no fixture pass may be inferred"
        elif marker_errors or len(seen) != len(cases):
            report["runnerError"] = "; ".join(marker_errors + [f"missing native marker: {identity}" for identity in expected if identity not in seen])
            for case in cases:
                if (case["corpus"], case["category"], case["id"]) in seen:
                    case["outcome"] = "failed"
                    case["reason"] = "runner marker reconciliation failed"
                else:
                    case["outcome"] = "unresolved"
                    case["reason"] = "no marker emitted by passing test process"
        else:
            for case in cases:
                case["outcome"] = "passed"
            run(["swift", "build", "-c", "release"])
            verify_local_consumer()
            report["consumer"] = "passed"
            report["swiftVerification"] = "passed"
    except Exception as error:
        report["runnerError"] = str(error)
        for case in cases:
            case["outcome"] = "unresolved"
            case["reason"] = "verification runner failed before a completed verification pass"
    report["nativeCaseReport"]["totals"] = totals(cases)
    report["nativeCaseReport"]["nonPass"] = [
        {key: case[key] for key in ("corpus", "category", "id", "outcome", "reason") if key in case}
        for case in cases if case["outcome"] != "passed"
    ]
    write_report(report)
    print(json.dumps(report, sort_keys=True))
    if report.get("swiftVerification") != "passed":
        raise RuntimeError(report.get("runnerError", "Swift verification did not pass"))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"Swift verification failed: {error}", file=sys.stderr)
        sys.exit(1)
