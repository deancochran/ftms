"""Full source verification; does not publish or operate Bluetooth equipment."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from corpus import PACKAGE, ROOT, generate_browser_data, provenance, sha256, validate


def dart() -> str:
    executable = os.environ.get("DART") or shutil.which("dart")
    if not executable:
        raise RuntimeError("Dart SDK required; set DART to its executable")
    return executable


def run(*args: str, cwd: Path = PACKAGE, output: Path | None = None, env=None) -> None:
    print("+", " ".join(map(str, args)), flush=True)
    if output:
        with output.open("w") as log:
            subprocess.run(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=1200)
    else:
        subprocess.run(args, cwd=cwd, env=env, check=True, timeout=1200)


def account_events(path: Path, identity: dict) -> dict:
    tests, outcomes, matrices = {}, {}, []
    finished = False
    errors = []
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # Non-protocol compiler preamble; never interpreted as a pass.
        match event.get("type"):
            case "testStart":
                tests[event["test"]["id"]] = event["test"]["name"]
            case "testDone":
                outcomes[event["testID"]] = event
            case "print":
                message = event.get("message", "")
                if message.startswith("FTMS_MATRIX:"):
                    matrices.append(json.loads(message.removeprefix("FTMS_MATRIX:")))
            case "error":
                errors.append(event.get("error", "Test runner error"))
            case "done":
                finished = event.get("success") is True
    executed = {}
    for test_id, name in tests.items():
        match = re.search(r"\[([a-z]+)/([^\]]+)\]", name)
        if not match:
            continue
        key = match.groups()
        if key in executed:
            errors.append(f"Duplicate registration: {key}")
        event = outcomes.get(test_id)
        status = "skipped" if not event or event.get("skipped") else (
            "passed" if event.get("result") == "success" else "failed")
        executed[key] = status
    report = {**identity, "runnerErrors": errors, "testProcessFinished": finished, "corpora": {}}
    expected_keys = set()
    for name, corpus in identity["corpora"].items():
        if name == "matrix":
            continue
        rows = []
        for case_id in corpus["caseIds"]:
            key = name, case_id
            expected_keys.add(key)
            status = executed.get(key, "unsupported")
            rows.append({"id": case_id, "outcome": status,
                         **({"reason": "No executed Dart driver"} if status == "unsupported" else {})})
        counts = {s: sum(r["outcome"] == s for r in rows)
                  for s in ("passed", "failed", "unsupported", "skipped")}
        report["corpora"][name] = {**corpus, "total": len(rows), **counts, "outcomes": rows,
                                   "complete": bool(rows) and counts["passed"] == len(rows)}
    expected_keys.add(("matrix", "all"))
    extra = set(executed) - expected_keys
    if extra:
        errors.append(f"Unrecognized conformance registrations: {sorted(extra)}")
    expected_matrix = {"structural": 181760, "directions": 363520, "sentinels": 46, "rfu": 47, "prefixes": 315}
    matrix_ok = (len(matrices) == 1 and matrices[0] == expected_matrix
                 and executed.get(("matrix", "all")) == "passed")
    report["corpora"]["matrix"] = {**identity["corpora"]["matrix"],
                                    "observedCounts": matrices, "requiredCounts": expected_matrix,
                                    "complete": matrix_ok}
    report["complete"] = finished and not errors and all(c["complete"] for c in report["corpora"].values())
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("vm", "chrome"), default="vm")
    parser.add_argument("--compiler", choices=("dart2js", "dart2wasm"))
    parser.add_argument("--package", action="store_true", help="Also verify publication contents and isolated consumer")
    args = parser.parse_args()
    if args.compiler and args.platform != "chrome":
        parser.error("Web compilers require --platform chrome")
    output = PACKAGE / "build" / (args.platform + ("-" + args.compiler if args.compiler else ""))
    output.mkdir(parents=True, exist_ok=True)
    # Replace stale evidence with an explicitly incomplete record before doing work.
    destination = output / "verification.json"
    destination.write_text(json.dumps({"complete": False, "phase": "starting"}) + "\n")
    identity = validate()
    identity["toolchain"] = subprocess.check_output([dart(), "--version"], text=True).strip()
    identity["platform"] = args.platform
    identity["compiler"] = args.compiler
    identity["runnerHashes"] = {str(p.relative_to(PACKAGE)): sha256(p)
                                for directory in ("lib", "test", "tool")
                                for p in sorted((PACKAGE / directory).rglob("*"))
                                if p.is_file() and p.suffix in (".dart", ".py")
                                and not p.name.endswith(".g.dart")}
    (output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    generate_browser_data()
    run(dart(), "pub", "get")
    shutil.copyfile(PACKAGE / "pubspec.lock", output / "pubspec.lock")
    identity["dependencyLockSha256"] = sha256(output / "pubspec.lock")
    (output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    run(dart(), "format", "test/support/corpus_browser.g.dart")
    run(sys.executable, "-m", "unittest", "discover", "-s", "tool", "-p", "test_*.py")
    run(dart(), "format", "--output=none", "--set-exit-if-changed", "lib", "test", "example")
    run(dart(), "analyze", "--fatal-infos")
    command = [dart(), "test", "--platform", args.platform, "--reporter", "json"]
    if args.compiler:
        command.extend(("--compiler", args.compiler))
    test_error = None
    try:
        run(*command, output=output / "tests.jsonl")
    except subprocess.CalledProcessError as error:
        test_error = str(error)
    report = account_events(output / "tests.jsonl", identity)
    if test_error:
        report["runnerErrors"].append(test_error)
        report["complete"] = False
    if provenance() != {k: identity[k] for k in ("sourceCommit", "dirty")}:
        report["runnerErrors"].append("Source provenance changed during execution")
        report["complete"] = False
    destination.write_text(json.dumps(report, indent=2) + "\n")
    if not report["complete"]:
        raise RuntimeError(f"Incomplete conformance: inspect {destination} and tests.jsonl")
    report["conformanceComplete"] = True
    report["complete"] = False
    report["phase"] = "post-test verification"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    try:
        run(dart(), "doc", output=output / "dartdoc.log")
        report["documentationGenerated"] = True
        if args.package:
            run(sys.executable, "tool/verify_package.py")
            report["isolatedPackageVerified"] = True
        current_hashes = {str(p.relative_to(PACKAGE)): sha256(p)
                          for directory in ("lib", "test", "tool")
                          for p in sorted((PACKAGE / directory).rglob("*"))
                          if p.is_file() and p.suffix in (".dart", ".py")
                          and not p.name.endswith(".g.dart")}
        if current_hashes != identity["runnerHashes"]:
            raise RuntimeError("Runtime or runner sources changed during verification")
        if sha256(PACKAGE / "pubspec.lock") != identity["dependencyLockSha256"]:
            raise RuntimeError("Dependency resolution changed during verification")
        report["complete"] = True
        report["phase"] = "verified"
    except Exception as error:
        report["runnerErrors"].append(str(error))
        raise
    finally:
        destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Complete {args.platform} conformance: {destination}")


if __name__ == "__main__":
    main()
