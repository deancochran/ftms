#!/usr/bin/env python3
"""Host-only v1 corpus adapter; the target library neither embeds nor parses JSON."""
import hashlib
import json
import math
import subprocess
import sys
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from control_adapter import call as control_call, exact

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "shared/conformance/v1"
CATEGORY_KEYS = (
    "features", "ranges", "controls", "controlResponses", "measurements", "statuses", "diagnostics"
)
MACHINE_FIELDS = (
    "averageSpeedSupported", "cadenceSupported", "totalDistanceSupported", "inclinationSupported",
    "elevationGainSupported", "paceSupported", "stepCountSupported", "resistanceLevelSupported",
    "strideCountSupported", "expendedEnergySupported", "heartRateMeasurementSupported",
    "metabolicEquivalentSupported", "elapsedTimeSupported", "remainingTimeSupported",
    "powerMeasurementSupported", "forceOnBeltSupported", "userDataRetentionSupported",
)
TARGET_FIELDS = (
    "speedTargetSettingSupported", "inclinationTargetSettingSupported", "resistanceTargetSettingSupported",
    "powerTargetSettingSupported", "heartRateTargetSettingSupported", "targetedExpendedEnergySupported",
    "targetedStepNumberSupported", "targetedStrideNumberSupported", "targetedDistanceSupported",
    "targetedTrainingTimeSupported", "targetedTimeTwoHRZonesSupported",
    "targetedTimeThreeHRZonesSupported", "targetedTimeFiveHRZonesSupported",
    "indoorBikeSimulationSupported", "wheelCircumferenceSupported", "spinDownControlSupported",
    "targetedCadenceSupported",
)
RANGE_UNITS = {
    "speed": (100, 0, "km/h"), "inclination": (10, 1, "percent"),
    "resistance": (1, 2, "level"), "heartRate": (1, 3, "bpm"), "power": (1, 4, "watts"),
}
ERROR_CODES = {"length": 2, "range": 4}
MEASUREMENT_KINDS = {
    "00002acd-0000-1000-8000-00805f9b34fb": 0, "00002ace-0000-1000-8000-00805f9b34fb": 1,
    "00002acf-0000-1000-8000-00805f9b34fb": 2, "00002ad0-0000-1000-8000-00805f9b34fb": 3,
    "00002ad1-0000-1000-8000-00805f9b34fb": 4, "00002ad2-0000-1000-8000-00805f9b34fb": 5,
}
METRICS = {
    0: ("speedMps", 360), 1: ("averageSpeedMps", 360), 2: ("distanceMeters", 1),
    3: ("inclinationPercent", 10), 4: ("rampAngleDegrees", 10), 5: ("positiveElevationGainMeters", None),
    6: ("negativeElevationGainMeters", None), 7: ("instantaneousPaceSecondsPer500m", 1),
    8: ("averagePaceSecondsPer500m", 1), 9: ("energyKcal", 1), 10: ("energyPerHourKcal", 1),
    11: ("energyPerMinuteKcal", 1), 12: ("hrBpm", 1), 13: ("metabolicEquivalent", 10),
    14: ("elapsedTimeSeconds", 1), 15: ("remainingTimeSeconds", 1), 16: ("forceOnBeltNewtons", 1),
    17: ("powerWatts", 1), 18: ("stepRateSpm", 1), 19: ("averageStepRateSpm", 1),
    20: ("strideCount", None), 21: ("resistanceLevel", 1), 22: ("averagePowerWatts", 1),
    23: ("floorCount", 1), 24: ("stepCount", 1), 25: ("strokeRateSpm", 2),
    26: ("strokeCount", 1), 27: ("averageStrokeRateSpm", 2), 28: ("cadenceRpm", 2), 29: ("averageCadenceRpm", 2),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def feature_object(machine, target):
    actual = {name: bool(machine & (1 << bit)) for bit, name in enumerate(MACHINE_FIELDS)}
    actual.update({name: bool(target & (1 << bit)) for bit, name in enumerate(TARGET_FIELDS)})
    actual["supportsERG"] = actual["powerTargetSettingSupported"]
    actual["supportsSIM"] = actual["indoorBikeSimulationSupported"]
    actual["supportsResistance"] = actual["resistanceTargetSettingSupported"]
    return actual


def compare_feature(case, result):
    if len(result) != 3 or result[0] != "ok":
        return False, "expected feature success"
    try:
        actual = feature_object(int(result[1]), int(result[2]))
    except ValueError:
        return False, "invalid feature word output"
    if "expected" in case:
        if actual != case["expected"]:
            return False, "feature object mismatch"
    elif "expectedTrue" in case:
        if {name for name, value in actual.items() if value} != set(case["expectedTrue"]):
            return False, "feature true-field set mismatch"
    else:
        return False, "feature case has no comparison expectation"
    return True, ""


def compare_range(case, result):
    if "expectedError" in case:
        expected = ERROR_CODES.get(case["expectedError"])
        if expected is None:
            return False, "unknown expected error"
        return (result == ["error", str(expected)], "range error mismatch")
    if "expected" not in case or case["kind"] not in RANGE_UNITS:
        return False, "range case has no supported expectation"
    if len(result) != 7 or result[0] != "ok":
        return False, "expected range success"
    if result[1] != case["kind"]:
        return False, "range kind mismatch"
    try:
        minimum, maximum, increment, divisor, unit = map(int, result[2:])
    except ValueError:
        return False, "invalid range output"
    expected_divisor, expected_unit, expected_unit_name = RANGE_UNITS[case["kind"]]
    if divisor != expected_divisor or unit != expected_unit:
        return False, "range divisor or unit mismatch"
    expected = case["expected"]
    actual = {
        "kind": case["kind"], "min": minimum / divisor, "max": maximum / divisor,
        "increment": increment / divisor, "unit": expected_unit_name,
    }
    expected_object = {"kind": case["kind"], **expected}
    if actual != expected_object:
        return False, "range value mismatch"
    return True, ""


def invoke(driver, kind, bytes_):
    output = subprocess.check_output([str(driver), kind, bytes(bytes_).hex()], text=True)
    return output.strip().split()


def validate_corpus():
    try:
        import jsonschema
    except ImportError as error:
        raise RuntimeError("jsonschema unavailable; schema validation is required") from error
    schema = json.loads((CORPUS / "schema.json").read_text())
    data = json.loads((CORPUS / "vectors.json").read_text())
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as error:
        raise RuntimeError("schema validation failed: " + error.message) from error
    return data, "jsonschema " + version("jsonschema")


def control_arguments(request):
    names = ["requestControl", "reset", "setTargetSpeed", "setTargetInclination", "setTargetResistance",
             "setTargetPower", "setTargetHeartRate", "startResume", "stopPause", "setTargetedExpendedEnergy",
             "setTargetedSteps", "setTargetedStrides", "setTargetedDistance", "setTargetedTrainingTime",
             "setTargetedTimeTwoHrZones", "setTargetedTimeThreeHrZones", "setTargetedTimeFiveHrZones",
             "setIndoorBikeSimulation", "setWheelCircumference", "spinDown", "setTargetedCadence"]
    opcode = names.index(request["op"])
    def scaled(key, scale=1):
        value = Decimal(str(request[key])) * scale
        if value != value.to_integral_value():
            raise ValueError("fixture value not exactly representable in native raw units")
        return int(value)
    scalar = {2: ("speedKph", 100), 3: ("inclinationPercent", 10), 4: ("resistanceLevel", 10),
              5: ("powerWatts", 1), 6: ("heartRateBpm", 1), 9: ("energyKcal", 1),
              10: ("steps", 1), 11: ("strides", 1), 12: ("distanceMeters", 1), 13: ("seconds", 1),
              18: ("circumferenceMm", 10), 20: ("cadenceRpm", 2)}
    if opcode in scalar:
        operands = [scaled(*scalar[opcode])]
    elif opcode in (8, 19):
        operands = [{"stop": 1, "pause": 2, "start": 1, "ignore": 2}[request["action"]]]
    elif opcode in (14, 15, 16):
        operands = request["seconds"]
    elif opcode == 17:
        operands = [scaled("windSpeedMps", 1000), scaled("gradePercent", 100), scaled("crr", 10000), scaled("cwKgPerM", 100)]
    else:
        operands = []
    return ["encode-request", opcode, *operands]


def compare_control_request(case, actual):
    return exact(actual, {"bytes": bytes(case["expectedBytes"]).hex()}), "control bytes mismatch"


def compare_control_response(case, raw):
    # The native evidence decoder retains nonconformant header/extra-parameter
    # diagnostics. Codec-v1's validated-response view treats these as malformed.
    malformed = raw.get("error") in (2, 3) or raw.get("unknownRequest") == 1 or raw.get("unexpectedParameters") == 1
    if "expectedError" in case:
        return malformed and case["expectedError"] == "malformed_response", "control response error mismatch"
    required = {"requestOpcode", "resultCode", "parameter", "low", "high", "unknownRequest", "unknownResult", "unexpectedParameters"}
    if malformed or set(raw) != required:
        return False, "expected complete response evidence"
    code = raw["resultCode"]
    names = {1: "success", 2: "not_supported", 3: "invalid_parameter", 4: "operation_failed", 5: "control_not_permitted"}
    actual = {"requestOpCode": raw["requestOpcode"], "resultCode": code,
              "resultCodeName": names.get(code, f"unknown_0x{code:02x}"), "success": code == 1,
              "parameter": {"kind": "none"}, "issues": ["reserved_value"] if raw["unknownResult"] else []}
    if raw["parameter"] == 1:
        actual["parameter"] = {"kind": "spin_down_speeds", "targetSpeedLowKph": raw["low"] / 100,
                               "targetSpeedHighKph": raw["high"] / 100}
    elif raw["parameter"] != 0:
        return False, "invalid response parameter tag"
    # v1 values may spell exact integral quantities as ints; compare their
    # normalized numeric values, while the separate raw corpus is integer-exact.
    return actual == case["expected"], "control response fields mismatch"


def measurement_raw(driver, case):
    kind = MEASUREMENT_KINDS.get(case.get("characteristicUuid"))
    if kind is None:
        return None
    return control_call(driver, "decode", kind, bytes(case["bytes"]).hex())


def measurement_projection(raw):
    metrics = {}
    for index, (name, divisor) in METRICS.items():
        if not raw["present"] & (1 << index):
            continue
        if raw["unavailable"] & (1 << index):
            metrics[name] = None
            continue
        if divisor is None:
            divisor = 10 if index == 20 and raw["kind"] == 1 else (10 if index in (5, 6) and raw["kind"] == 0 else 1)
        metrics[name] = raw["values"][index] / divisor
    # A flagged but incomplete field is null in codec-v1's metric projection,
    # while the native raw API correctly leaves its physically-read bit unset.
    # This is derived from actual decoded flags, never fixture input bytes.
    if raw["truncated"]:
        groups = [
            [[0],[1],[2],[3,4],[5,6],[7],[8],[9,10,11],[12],[13],[14],[15],[16,17]],
            [[0],[1],[2],[18,19],[20],[5,6],[3,4],[21],[17],[22],[9,10,11],[12],[13],[14],[15]],
            [[23,24],[18],[19],[5],[9,10,11],[12],[13],[14],[15]],
            [[23],[18],[19],[5],[20],[9,10,11],[12],[13],[14],[15]],
            [[25,26],[27],[2],[7],[8],[17],[22],[21],[9,10,11],[12],[13],[14],[15]],
            [[0],[1],[28],[29],[2],[21],[17],[22],[9,10,11],[12],[13],[14],[15]],
        ]
        for flag, fields in enumerate(groups[raw["kind"]]):
            active = not (raw["flags"] & 1) if flag == 0 else raw["flags"] & (1 << flag)
            if active:
                for field in fields:
                    if not raw["present"] & (1 << field):
                        metrics[METRICS[field][0]] = None
    if raw["kind"] == 1:
        metrics["movementDirection"] = "backward" if raw["backward"] else "forward"
    return metrics


def metric_subset(expected, actual):
    for key, value in expected.items():
        if key not in actual:
            return False
        got = actual[key]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not isinstance(got, (int, float)) or isinstance(got, bool) or not math.isfinite(got) or abs(got - value) >= .005:
                return False
        elif got != value:
            return False
    return True


def compare_measurement(case, raw, diagnostic=False):
    if "error" in raw:
        return False, "native measurement error"
    metrics = measurement_projection(raw)
    expected_metrics = case.get("expectedMetrics", {})
    if not metric_subset(expected_metrics, metrics):
        return False, "measurement metrics mismatch"
    if diagnostic:
        if bool(raw["truncated"]) != case["expectedTruncated"]:
            return False, "truncated mismatch"
        issues = set()
        if raw["moreData"]: issues.add("more_data")
        if raw["truncated"]: issues.add("truncated")
        if raw["trailingBytes"]: issues.add("trailing_bytes")
        if raw["reservedFlags"]: issues.add("reserved_flags")
        if raw["unavailable"]: issues.add("unavailable")
        if not set(case["expectedIssues"]).issubset(issues):
            return False, "measurement diagnostic issues mismatch"
    return True, ""


def subset(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and subset(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(subset(a, b) for a, b in zip(expected, actual))
    if isinstance(expected, bool) or expected is None:
        return type(expected) is type(actual) and expected == actual
    return expected == actual


def compare_status_output(case, raw):
    is_machine = case["characteristicUuid"] == "00002ada-0000-1000-8000-00805f9b34fb"
    if "error" in raw: return False, "native status error"
    actual_code = raw["opcode"] if is_machine else raw["code"]
    if "expectedStatus" in case:
        if not is_machine:
            # Only currently canonical labels are projected; unsupported future
            # status expectations fail rather than ignoring their fields.
            if actual_code != 13:
                return False, "training status projection has no expected semantic mapping"
            label = "manual_mode"
            details = {"kind": "training_status", "flags": raw["flags"], "stringPresent": bool(raw["textPresent"]),
                       "extendedStringPresent": bool(raw["extendedString"]),
                       "trainingStatusString": bytes.fromhex(raw["textHex"]).decode("utf-8", "replace") if raw["textPresent"] else None}
        else:
            parameter = raw["parameter"]
            if actual_code == 5 and parameter is not None and parameter["opcode"] == 2:
                label, details = "target_speed_changed", {"kind": "speed", "speedKph": parameter["operands"][0] / 100}
            elif actual_code == 18 and parameter is not None and parameter["opcode"] == 17:
                values = parameter["operands"]
                label, details = "indoor_bike_simulation_parameters_changed", {"kind": "simulation", "windSpeedMps": values[0] / 1000,
                    "gradePercent": values[1] / 100, "crr": values[2] / 10000, "cwKgPerM": values[3] / 100}
            elif actual_code == 255 and parameter is None:
                label, details = "control_permission_lost", {"kind": "none"}
            else:
                return False, "status projection has no expected semantic mapping"
        return subset(case["expectedStatus"], {"code": actual_code, "label": label, "details": details}), "status field mismatch"
    # Codec-v1 represents an unread status code as null, rather than the raw
    # decoder's zero-initialized storage. The evidence flags distinguish it.
    if raw["truncated"] and (not is_machine or (raw["unknownOpcode"] and actual_code == 0)):
        actual_code = None
    if "expectedStatusCode" in case and actual_code != case["expectedStatusCode"]:
        return False, "diagnostic status code mismatch"
    issues=set()
    for key,name in (("unknownOpcode","unknown_opcode"),("reservedValue","reserved_value"),("truncated","truncated"),("trailingBytes","trailing_bytes"),("reservedFlags","reserved_flags"),("invalidFlags","invalid_flags"),("invalidUtf8","invalid_utf8")):
        if raw.get(key): issues.add(name)
    return (bool(raw["truncated"]) == case["expectedTruncated"] and set(case["expectedIssues"]).issubset(issues)), "status diagnostic mismatch"


def compare_status(case, driver):
    operation = "decode-machine" if case["characteristicUuid"] == "00002ada-0000-1000-8000-00805f9b34fb" else "decode-training"
    return compare_status_output(case, control_call(driver, operation, bytes(case["bytes"]).hex()))

def run(driver, control_driver=None, measurement_driver=None, status_driver=None):
    data, validation = validate_corpus()
    counts = {category: len(data[category]) for category in CATEGORY_KEYS}
    ids = [case["id"] for category in CATEGORY_KEYS for case in data[category]]
    duplicate_ids = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    failures = []
    passed = 0
    for case in data["features"]:
        ok, reason = compare_feature(case, invoke(driver, "feature", case["bytes"]))
        if ok:
            passed += 1
        else:
            failures.append(f"{case['id']}: {reason}")
    for case in data["ranges"]:
        ok, reason = compare_range(case, invoke(driver, case["kind"], case["bytes"]))
        if ok:
            passed += 1
        else:
            failures.append(f"{case['id']}: {reason}")
    if control_driver is not None:
        for case in data["controls"]:
            ok, reason = compare_control_request(case, control_call(control_driver, *control_arguments(case["request"])))
            if ok:
                passed += 1
            else:
                failures.append(f"{case['id']}: {reason}")
        for case in data["controlResponses"]:
            ok, reason = compare_control_response(case, control_call(control_driver, "decode-response", bytes(case["bytes"]).hex()))
            if ok:
                passed += 1
            else:
                failures.append(f"{case['id']}: {reason}")
    if measurement_driver is not None:
        for case in data["measurements"]:
            ok, reason = compare_measurement(case, measurement_raw(measurement_driver, case))
            if ok: passed += 1
            else: failures.append(f"{case['id']}: {reason}")
        for case in data["diagnostics"]:
            if case.get("characteristicUuid") not in MEASUREMENT_KINDS:
                continue
            ok, reason = compare_measurement(case, measurement_raw(measurement_driver, case), True)
            if ok: passed += 1
            else: failures.append(f"{case['id']}: {reason}")
    if status_driver is not None:
        for case in data["statuses"] + [x for x in data["diagnostics"] if x.get("characteristicUuid") in ("00002ad3-0000-1000-8000-00805f9b34fb", "00002ada-0000-1000-8000-00805f9b34fb")]:
            ok, reason = compare_status(case, status_driver)
            if ok: passed += 1
            else: failures.append(f"{case['id']}: {reason}")
    unsupported = [
        f"{case['id']}: unsupported outside first C slice"
        for category in CATEGORY_KEYS[4 if control_driver is not None else 2:]
        for case in data[category]
        if not (measurement_driver is not None and
                (category == "measurements" or (category == "diagnostics" and case.get("characteristicUuid") in MEASUREMENT_KINDS)))
    ]
    if status_driver is not None:
        unsupported = [item for item in unsupported if not (item.startswith("status-") or item.startswith("diagnostic-training-") or item.startswith("diagnostic-machine-"))]
    if duplicate_ids:
        failures.extend(f"duplicate ID: {case_id}" for case_id in duplicate_ids)
    checkout = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    print(f"corpus schemaVersion={data['schemaVersion']} validation={validation} checkout={checkout} dirty={dirty}")
    print("sha256 schema=%s vectors=%s contract=%s" % (
        sha256(CORPUS / "schema.json"), sha256(CORPUS / "vectors.json"), sha256(ROOT / "shared/conformance/README.md")))
    complete = not failures and not unsupported and passed == len(ids)
    print("cases total=%d %s passed=%d failed=%d unsupported=%d skipped=0 complete=%s" % (
        len(ids), " ".join(f"{key}={counts[key]}" for key in CATEGORY_KEYS),
        passed, len(failures), len(unsupported), str(complete).lower()))
    if failures:
        print("failures: " + "; ".join(failures))
    print("unsupported: " + "; ".join(unsupported))
    return 0 if not failures and passed + len(unsupported) == len(ids) else 1


def main(argv):
    if len(argv) not in (2, 3, 4, 5):
        print(f"usage: {argv[0]} DRIVER [CONTROL_DRIVER [MEASUREMENT_DRIVER]]", file=sys.stderr)
        return 64
    try:
        return run(Path(argv[1]), Path(argv[2]) if len(argv) >= 3 else None,
                   Path(argv[3]) if len(argv) >= 4 else None, Path(argv[4]) if len(argv) == 5 else None)
    except RuntimeError as error:
        print("RUNNER ERROR: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
