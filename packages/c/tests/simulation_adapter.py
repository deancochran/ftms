"""Deterministic host orchestration; no expected values cross the C bridge."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

if __package__:
    from . import capability_adapter, control_adapter
else:
    import capability_adapter
    import control_adapter

ROOT = Path(__file__).resolve().parents[3]
SIM = ROOT / "shared/simulation"
V = SIM / "v1"
IDENTITY_FILES = [
    "shared/simulation/README.md", "shared/simulation/v1/schema.json",
    "shared/simulation/v1/scenarios.json", "shared/protocol/wire-compatibility.md",
    "shared/protocol/capability-discovery.md",
    "shared/conformance/capabilities/v1/schema.json",
    "shared/conformance/capabilities/v1/vectors.json",
    "shared/conformance/capabilities/README.md",
    "shared/conformance/controls/v1/schema.json",
    "shared/conformance/controls/v1/vectors.json",
    "shared/conformance/controls/README.md",
]
REFERENCE_TYPES = ("capabilities", "control", "response")
DEFAULT_CORPUS = object()


def strict_equal(left, right):
    return capability_adapter.compare(left, right) is None


def load_references():
    capabilities = {case["id"]: case for case in capability_adapter.load_cases()}
    controls = control_adapter.validate()
    return {
        "capabilities": capabilities,
        "control": {case["id"]: case for case in controls["requests"]},
        "response": {case["id"]: case for case in controls["responses"]},
    }


def validateCorpus(data=DEFAULT_CORPUS):
    if data is DEFAULT_CORPUS:
        data = json.loads((V / "scenarios.json").read_text())
    schema = json.loads((V / "schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    errors = [f"{list(error.path)}: {error.message}"
              for error in Draft202012Validator(schema).iter_errors(data)]
    if errors:
        return errors
    references = load_references()
    profiles, scenarios = set(), set()
    for profile in data["profiles"]:
        if profile["id"] in profiles:
            errors.append("duplicate profile " + profile["id"])
        profiles.add(profile["id"])
    for scenario in data["scenarios"]:
        if scenario["id"] in scenarios:
            errors.append("duplicate scenario " + scenario["id"])
        scenarios.add(scenario["id"])
        if scenario["profile"] not in profiles:
            errors.append("missing profile " + scenario["profile"])
        for step in scenario["steps"]:
            if step["type"] in REFERENCE_TYPES and step["caseId"] not in references[step["type"]]:
                errors.append(f"missing {step['type']} case {step['caseId']}")
    return errors


def reference(step, directory, references):
    kind = step["type"]
    case = references[kind][step["caseId"]]
    if kind == "capabilities":
        process = subprocess.run(
            [str(directory / "capability-driver")],
            input=capability_adapter.line(case["input"]), text=True,
            capture_output=True, timeout=10, check=True,
        )
        return json.loads(process.stdout), case["expected"]
    driver = directory / "control-driver"
    operation = "request" if kind == "control" else "response"
    value = case["decoded"]
    format_args = [case["format"]] if kind == "control" and "format" in case else []
    command = "decode-" + operation + ("-format" if format_args else "")
    actual = {"decoded": control_adapter.call(driver, command, *format_args, bytes(case["bytes"]).hex())}
    expected = {"decoded": value}
    if case.get("encode", True):
        # Encode the authored value, NOT the result of decoding the same bytes.
        args = (["encode-request" + ("-format" if format_args else ""), *format_args, value["opcode"], *value["operands"]] if kind == "control"
                else ["encode-response", value["requestOpcode"], value["resultCode"],
                      value["parameter"], value["low"], value["high"]])
        encoded = control_adapter.call(driver, *args)
        actual["encoded"] = list(bytes.fromhex(encoded["bytes"]))
        expected["encoded"] = case["bytes"]
    return actual, expected


def bridge_commands(scenario, profile, base_tick):
    def init(operation, generation):
        return (f"{operation} {profile['kind']} {generation} {profile['maxAge']} "
                f"{profile['format']['resistance']} {profile['format']['pace']}")
    commands = [init("init", scenario["generation"])]
    indexes = {}
    for index, step in sorted(enumerate(scenario["steps"]), key=lambda item: (item[1]["at"], item[0])):
        tick = (base_tick + step["at"]) & 0xffffffff
        operation = step["type"]
        if operation in REFERENCE_TYPES or operation == "drop":
            continue
        indexes[index] = len(commands)
        if operation == "feed":
            commands.append(f"feed {step['generation']} {tick} {bytes(step['bytes']).hex() or '-'}")
        elif operation in ("reset", "disconnect"):
            commands.append(operation)
        else:
            commands.append(init("reconnect", step["generation"]))
    return commands, indexes


def runCorpus(driver, data=DEFAULT_CORPUS):
    if data is DEFAULT_CORPUS:
        data = json.loads((V / "scenarios.json").read_text())
    report = {
        "implementation": "c-production-record-assembler",
        "total": len(data.get("scenarios", [])) if isinstance(data, dict) and isinstance(data.get("scenarios"), list) else 0,
        "passed": 0, "failed": 0, "unsupported": 0, "skipped": 0,
        "steps": 0, "passedSteps": 0, "failedSteps": 0, "complete": False,
        "runnerErrors": [], "scenarios": [], "trace": [], "identity": {},
        "inputSha256": hashlib.sha256(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
    }
    try:
        report["identity"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in IDENTITY_FILES}
        report["sourceCommit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        report["runnerErrors"] = validateCorpus(data)
        if report["runnerErrors"]:
            return report
        references = load_references()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report["runnerErrors"].append(str(error))
        return report
    profiles = {profile["id"]: profile for profile in data["profiles"]}
    driver = Path(driver).resolve()
    for scenario in data["scenarios"]:
        commands, indexes = bridge_commands(scenario, profiles[scenario["profile"]], data.get("baseTick", 0))
        outputs, bridge_error = [], None
        try:
            process = subprocess.run([str(driver)], input="\n".join(commands) + "\n",
                                     text=True, capture_output=True, timeout=10, check=True)
            outputs = [json.loads(line) for line in process.stdout.splitlines()]
            if len(outputs) != len(commands) or not strict_equal(outputs[0], {"status": "pending"}):
                raise ValueError("bridge initialization or output count mismatch")
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            bridge_error = str(error)
            report["runnerErrors"].append(f"{scenario['id']}: {bridge_error}")
        ok = bridge_error is None
        for index, step in sorted(enumerate(scenario["steps"]), key=lambda item: (item[1]["at"], item[0])):
            expected, actual, reason = step.get("expected"), None, None
            try:
                if step["type"] in REFERENCE_TYPES:
                    actual, expected = reference(step, driver.parent, references)
                elif step["type"] == "drop":
                    actual = {"status": "dropped"}
                elif bridge_error:
                    actual, reason = {"exception": bridge_error}, "bridge failure"
                else:
                    actual = outputs[indexes[index]]
            except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
                actual, reason = {"exception": str(error)}, "exception"
            passed = reason is None and strict_equal(actual, expected)
            if not passed:
                ok = False
                reason = reason or "actual does not equal expected"
            report["steps"] += 1
            report["passedSteps" if passed else "failedSteps"] += 1
            trace = {"scenario": scenario["id"], "profile": scenario["profile"], "index": index,
                     "scheduledAt": step["at"], "at": (data.get("baseTick", 0) + step["at"]) & 0xffffffff,
                     "kind": step["type"], "actual": actual, "expected": expected,
                     "outcome": "passed" if passed else "failed"}
            if reason:
                trace["reason"] = reason
            report["trace"].append(trace)
        report["scenarios"].append({"id": scenario["id"], "outcome": "passed" if ok else "failed", "steps": len(scenario["steps"])})
        report["passed" if ok else "failed"] += 1
    report["complete"] = (report["total"] > 0 and report["passed"] == report["total"]
                          and report["steps"] == sum(len(s["steps"]) for s in data["scenarios"])
                          and report["failedSteps"] == 0 and not report["runnerErrors"])
    return report


def main(driver):
    report = runCorpus(driver)
    print(json.dumps({"simulation": report}, sort_keys=True))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
