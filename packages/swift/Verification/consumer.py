#!/usr/bin/env python3
"""Verify a public Git/revision SwiftPM consumer, optionally with Apple SDKs."""
import argparse
import json
import platform
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / ".build/swift-consumer-report.json"


def run(command, directory):
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=directory, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="https://github.com/deancochran/ftms.git")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--apple", action="store_true")
    args = parser.parse_args()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {"repository": args.repository, "revision": args.revision,
              "expectedCommit": args.expected_commit, "platform": platform.platform(),
              "toolchain": subprocess.check_output(["swift", "--version"], text=True).strip(),
              "passed": False, "appleBuilds": []}
    try:
        # Package caches and the entire build live inside a fresh isolated consumer.
        with tempfile.TemporaryDirectory(prefix="swift-git-consumer-", dir=ROOT / ".build") as temporary:
            directory = Path(temporary)
            (directory / "Sources/Usage").mkdir(parents=True)
            (directory / "Sources/Consumer").mkdir(parents=True)
            (directory / "Package.swift").write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(
  name: "SwiftFTMSConsumer",
  platforms: [.macOS(.v13), .iOS(.v16), .tvOS(.v16), .watchOS(.v9), .visionOS(.v1)],
  products: [.library(name: "FTMSConsumer", targets: ["Usage"]),
             .executable(name: "Consumer", targets: ["Consumer"])],
  dependencies: [.package(name: "FTMSDependency", url: REPOSITORY, revision: REVISION)],
  targets: [.target(name: "Usage", dependencies: [.product(name: "FTMS", package: "FTMSDependency")]),
            .executableTarget(name: "Consumer", dependencies: ["Usage"])])
'''.replace("REPOSITORY", json.dumps(args.repository)).replace("REVISION", json.dumps(args.revision)))
            (directory / "Sources/Usage/Usage.swift").write_text('''import FTMS

public func verifyFTMS() throws {
  let request = ControlRequest(opcode: 5, operands: [75])
  let encodedRequest = try encodeControlRequest(request)
  precondition(encodedRequest == [5, 75, 0])
  let response = try decodeControlResponseRaw([0x80, 5, 1])
  precondition(response.resultCode == 1 && !response.unknownRequest)
  let features = try decodeFeatures([1, 0, 0, 0, 8, 0, 0, 0])
  precondition(features.machine(0) && features.target(3))
  let measurement = try decodeMeasurement(.indoorBike, bytes: [0, 0, 100, 0])
  precondition(measurement.values[.speed] == 100)
  let encodedMeasurement = try encodeMeasurement(measurement)
  precondition(encodedMeasurement == [0, 0, 100, 0])
  let range = inspectRange(.resistance, bytes: [0, 0, 100, 0, 1, 0],
                           options: .init(resistance: .sint16Tenths))
  precondition(range.status == .valid && range.value?.maximum == 100)
  let capabilities = try evaluateCapabilities(.init(discovery: 2, scope: 1,
                                                   generation: 1, characteristics: []))
  precondition(capabilities.operations.count == 21)
}
''')
            (directory / "Sources/Consumer/main.swift").write_text('import Usage\ntry verifyFTMS()\nprint("FTMS public consumer passed")\n')
            run(["swift", "package", "--cache-path", str(directory / "cache"), "resolve"], directory)
            pins = json.loads((directory / "Package.resolved").read_text())["pins"]
            if len(pins) != 1 or pins[0]["state"]["revision"] != args.expected_commit:
                raise RuntimeError(f"unexpected resolved dependency identity: {pins}")
            report["resolvedCommit"] = pins[0]["state"]["revision"]
            run(["swift", "run", "--cache-path", str(directory / "cache"), "-c", "release", "Consumer"], directory)
            report["hostConsumer"] = "passed"
            if args.apple:
                report["xcode"] = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
                for name, destination, deployment in [
                    ("macos", "macOS", "MACOSX_DEPLOYMENT_TARGET=13.0"),
                    ("ios", "iOS", "IPHONEOS_DEPLOYMENT_TARGET=16.0"),
                    ("tvos", "tvOS", "TVOS_DEPLOYMENT_TARGET=16.0"),
                    ("watchos", "watchOS", "WATCHOS_DEPLOYMENT_TARGET=9.0"),
                    ("visionos", "visionOS", "XROS_DEPLOYMENT_TARGET=1.0"),
                ]:
                    run(["xcodebuild", "-scheme", "FTMSConsumer", "-configuration", "Release",
                         "-destination", f"generic/platform={destination}",
                         "-derivedDataPath", str(directory / f"apple-{name}"),
                         "-clonedSourcePackagesDirPath", str(directory / "apple-dependencies"),
                         "CODE_SIGNING_ALLOWED=NO", deployment, "build"], directory)
                    checkouts = list((directory / "apple-dependencies/checkouts").iterdir())
                    if len(checkouts) != 1:
                        raise RuntimeError("expected exactly one Xcode dependency checkout")
                    resolved = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkouts[0], text=True).strip()
                    if resolved != args.expected_commit:
                        raise RuntimeError(f"Xcode resolved a different commit: {resolved}")
                    report["appleBuilds"].append({"platform": name, "deployment": deployment,
                                                 "resolvedCommit": resolved, "passed": True})
            report["passed"] = True
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        REPORT.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
