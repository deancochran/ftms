#!/usr/bin/env python3
"""Accountable Python FTMS partial conformance runner (Features, ranges, Control Point)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, cast

import jsonschema

from deancochran_ftms import (
    ControlFormatOptions,
    ControlRequestRaw,
    ControlResponseRaw,
    FeaturesRaw,
    MeasurementFormatOptions,
    MeasurementRaw,
    RangeFormatOptions,
    RawCodecError,
    SupportedRangeRaw,
    decode_control_request_raw,
    decode_control_response_raw,
    decode_features,
    decode_features_raw,
    decode_machine_status_raw,
    decode_measurement_raw,
    decode_supported_range,
    decode_supported_range_raw,
    decode_training_status_raw,
    encode_control_request_raw,
    encode_control_response_raw,
    encode_features_raw,
    encode_measurement_raw,
    encode_supported_range_raw,
    inspect_supported_range_raw,
    normalize_machine_status,
    normalize_measurement,
    normalize_training_status,
)

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
CATS = (
    "features",
    "ranges",
    "controls",
    "controlResponses",
    "measurements",
    "statuses",
    "diagnostics",
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load(d: Path) -> dict[str, Any]:
    s = json.loads((d / "schema.json").read_text())
    v = json.loads((d / "vectors.json").read_text())
    jsonschema.Draft202012Validator.check_schema(s)
    jsonschema.validate(v, s)
    return cast(dict[str, Any], v)


_ensure_unique_ids = None  # compatibility alias assigned below


def _unique(groups: dict[str, list[dict[str, Any]]]) -> None:
    ids = [x["id"] for xs in groups.values() for x in xs]
    if len(ids) != len(set(ids)):
        raise ValueError(
            "duplicate fixture IDs: " + ", ".join(sorted({x for x in ids if ids.count(x) > 1}))
        )


_ensure_unique_ids = _unique


def _out(i: str, c: str, direction: str | None, passed: bool, reason: str = "") -> dict[str, str]:
    r = {"id": i, "category": c, "outcome": "passed" if passed else "failed", "reason": reason}
    if direction:
        r["direction"] = direction
    return r


def _counts(xs: list[dict[str, str]]) -> dict[str, int]:
    return {
        k: sum(x["outcome"] == k for x in xs)
        for k in ("passed", "failed", "unsupported", "skipped")
    }


def _hashes(d: Path) -> dict[str, str]:
    return {
        str(x.relative_to(ROOT)): _sha(x)
        for x in (d / "schema.json", d / "vectors.json", d.parent / "README.md")
    }


def _opts(c: dict[str, Any]) -> RangeFormatOptions | ControlFormatOptions | None:
    o = c.get("options") or {}
    f = o.get("resistanceFormat")
    return None if f is None else RangeFormatOptions(f)


def _raw_dict(r: SupportedRangeRaw) -> dict[str, Any]:
    return {
        "minimum": r.minimum,
        "maximum": r.maximum,
        "increment": r.increment,
        "scaleDivisor": r.scale_divisor,
        "unit": {"speed": 0, "inclination": 1, "resistance": 2, "heartRate": 3, "power": 4}[r.kind],
        "kind": r.kind,
    }


def _complete(outcomes: list[dict[str, str]], expected: set[tuple[str, str | None]]) -> bool:
    """Require one outcome for every declared directional assertion, no more or less."""
    actual = [(item["id"], item.get("direction")) for item in outcomes]
    return bool(expected) and len(actual) == len(set(actual)) and set(actual) == expected


def measurement_expected(e: dict[str, Any]) -> MeasurementRaw:
    return MeasurementRaw(
        e["kind"],
        e["flags"],
        e["present"],
        e["unavailable"],
        tuple(e["values"]),
        e["moreData"],
        e["backward"],
        e["truncated"],
        e["trailingBytes"],
        e["reservedFlags"],
        e["bytesRead"],
    )


def _subset(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _subset(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(_subset(a, e) for a, e in zip(actual, expected, strict=True))
        )
    if type(expected) in (float, int) and type(actual) in (float, int):
        return bool(abs(actual - expected) < 0.005)
    return type(actual) is type(expected) and actual == expected


def _measurement_kind(uuid: str) -> int:
    return ("2acd", "2ace", "2acf", "2ad0", "2ad1", "2ad2").index(uuid[4:8])


def _diagnostic_matches(case: dict[str, Any]) -> bool:
    fields: tuple[tuple[int, str], ...]
    short = case["characteristicUuid"][4:8]
    data = bytes(case["bytes"])
    issues: list[str] = []
    if short in ("2acd", "2ace", "2acf", "2ad0", "2ad1", "2ad2"):
        raw = decode_measurement_raw(data, _measurement_kind(case["characteristicUuid"]))
        for flag, name in (
            (raw.more_data, "more_data"),
            (raw.unavailable, "unavailable"),
            (raw.truncated, "truncated"),
            (raw.trailing_bytes, "trailing_bytes"),
            (raw.reserved_flags, "reserved_flags"),
        ):
            if flag:
                issues.append(name)
        return (
            bool(raw.truncated) == case["expectedTruncated"]
            and set(issues) == set(case["expectedIssues"])
            and _subset(normalize_measurement(raw), case.get("expectedMetrics", {}))
        )
    if short == "2ad3":
        training = decode_training_status_raw(data)
        truncated = bool(training.truncated)
        code = None if truncated else training.code
        fields = (
            (training.reserved_flags, "reserved_flags"),
            (training.invalid_flags, "invalid_flags"),
            (training.reserved_value, "reserved_value"),
            (training.invalid_utf8, "invalid_utf8"),
            (training.trailing_bytes, "trailing_bytes"),
            (training.truncated, "truncated"),
        )
    else:
        machine = decode_machine_status_raw(data)
        truncated = bool(machine.truncated)
        code = None if not data else machine.opcode
        fields = (
            (machine.unknown_opcode if data else 0, "unknown_opcode"),
            (machine.reserved_value, "reserved_value"),
            (machine.trailing_bytes, "trailing_bytes"),
            (machine.truncated, "truncated"),
        )
    issues = [name for flag, name in fields if flag]
    return (
        truncated == case["expectedTruncated"]
        and code == case["expectedStatusCode"]
        and set(issues) == set(case["expectedIssues"])
    )


def run(v1_directory: Path | None = None, values_directory: Path | None = None) -> dict[str, Any]:
    v1 = v1_directory or ROOT / "shared/conformance/v1"
    values = values_directory or ROOT / "shared/conformance/values/v1"
    controls = ROOT / "shared/conformance/controls/v1"
    compat = ROOT / "shared/conformance/compatibility/v1"
    inspect = ROOT / "shared/conformance/inspection/v1"
    report: dict[str, Any] = {
        "package": "deancochran-ftms",
        "packageVersion": "0.1.0a1",
        "sourceCommit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "runnerErrors": [],
    }
    try:
        a, b, c, d = _load(v1), _load(values), _load(controls), _load(compat)
        fi = json.loads((inspect / "fixtures.json").read_text())
        si = (
            json.loads((inspect / "schema.json").read_text())
            if (inspect / "schema.json").exists()
            else None
        )
        if si:
            jsonschema.validate(fi, si)
        _unique({k: a[k] for k in CATS})
        for cases in {
            "values": b["cases"],
            "controls": c["requests"] + c["responses"] + c["invalid"],
            "compat": d["cases"],
            "inspect": fi["cases"],
        }.values():
            _unique({"cases": cases})
        outs = []
        for cat in CATS:
            for x in a[cat]:
                try:
                    if cat == "measurements":
                        normalized = normalize_measurement(
                            decode_measurement_raw(
                                bytes(x["bytes"]), _measurement_kind(x["characteristicUuid"])
                            )
                        )
                        ok = _subset(normalized, x["expectedMetrics"])
                    elif cat == "statuses":
                        normalized_status = (
                            normalize_training_status(decode_training_status_raw(bytes(x["bytes"])))
                            if x["characteristicUuid"][4:8] == "2ad3"
                            else normalize_machine_status(
                                decode_machine_status_raw(bytes(x["bytes"]))
                            )
                        )
                        ok = _subset(normalized_status, x["expectedStatus"])
                    elif cat == "diagnostics":
                        ok = _diagnostic_matches(x)
                    elif cat == "ranges" and "expectedError" in x:
                        try:
                            decode_supported_range(bytes(x["bytes"]), x["kind"])
                            ok = False
                        except RawCodecError as e:
                            ok = e.code == x["expectedError"]
                    elif cat == "controlResponses" and "expectedError" in x:
                        try:
                            invalid_response = decode_control_response_raw(bytes(x["bytes"]))
                            ok = bool(
                                x["expectedError"] == "malformed_response"
                                and (
                                    invalid_response.unknown_request
                                    or invalid_response.unexpected_parameters
                                )
                            )
                        except RawCodecError:
                            ok = x["expectedError"] == "malformed_response"
                    elif cat == "features":
                        feature_result = decode_features(bytes(x["bytes"]))
                        actual = (
                            {
                                "".join(
                                    [
                                        p if n == 0 else ("HR" if p == "hr" else p.title())
                                        for n, p in enumerate(k.split("_"))
                                    ]
                                ): getattr(feature_result.value, k)
                                for k in feature_result.value.__dataclass_fields__
                            }
                            if feature_result.value
                            else {}
                        )
                        actual.update(
                            supportsERG=feature_result.value.supports_erg,
                            supportsSIM=feature_result.value.supports_sim,
                            supportsResistance=feature_result.value.supports_resistance,
                        ) if feature_result.value else None
                        ok = (
                            actual == x.get("expected")
                            if "expected" in x
                            else {k for k, v in actual.items() if v} == set(x["expectedTrue"])
                        )
                    elif cat == "ranges":
                        r = decode_supported_range(bytes(x["bytes"]), x["kind"])
                        ok = {
                            "min": r.minimum,
                            "max": r.maximum,
                            "increment": r.increment,
                            "unit": r.unit,
                            "kind": r.kind,
                        } == {**x["expected"], "kind": x["kind"]}
                    elif cat == "controls":
                        # Independent fixture request values, never a decode result.
                        op = {
                            "requestControl": 0,
                            "reset": 1,
                            "setTargetSpeed": 2,
                            "setTargetInclination": 3,
                            "setTargetResistance": 4,
                            "setTargetPower": 5,
                            "setTargetHeartRate": 6,
                            "startResume": 7,
                            "stopPause": 8,
                            "setTargetedExpendedEnergy": 9,
                            "setTargetedSteps": 10,
                            "setTargetedStrides": 11,
                            "setTargetedDistance": 12,
                            "setTargetedTrainingTime": 13,
                            "setTargetedTimeTwoHrZones": 14,
                            "setTargetedTimeThreeHrZones": 15,
                            "setTargetedTimeFiveHrZones": 16,
                            "setIndoorBikeSimulation": 17,
                            "setWheelCircumference": 18,
                            "spinDown": 19,
                            "setTargetedCadence": 20,
                        }[x["request"]["op"]]
                        q = x["request"]
                        vals = []
                        fields = {
                            2: ("speedKph", 100),
                            3: ("inclinationPercent", 10),
                            4: ("resistanceLevel", 10),
                            5: ("powerWatts", 1),
                            6: ("heartRateBpm", 1),
                            9: ("energyKcal", 1),
                            10: ("steps", 1),
                            11: ("strides", 1),
                            12: ("distanceMeters", 1),
                            13: ("seconds", 1),
                            18: ("circumferenceMm", 10),
                            20: ("cadenceRpm", 2),
                        }
                        if op in fields:
                            vals = [round(q[fields[op][0]] * fields[op][1])]
                        elif op in (14, 15, 16):
                            vals = q["seconds"]
                        elif op == 8:
                            vals = [1 if q["action"] == "stop" else 2]
                        elif op == 19:
                            vals = [1 if q["action"] == "start" else 2]
                        elif op == 17:
                            vals = [
                                round(q["windSpeedMps"] * 1000),
                                round(q["gradePercent"] * 100),
                                round(q["crr"] * 10000),
                                round(q["cwKgPerM"] * 100),
                            ]
                        ok = encode_control_request_raw(
                            ControlRequestRaw(op, tuple(vals))
                        ) == bytes(x["expectedBytes"])
                    elif cat == "controlResponses":
                        z = decode_control_response_raw(bytes(x["bytes"]))
                        names = {
                            1: "success",
                            2: "not_supported",
                            3: "invalid_parameter",
                            4: "operation_failed",
                            5: "control_not_permitted",
                        }
                        p = (
                            {
                                "kind": "spin_down_speeds",
                                "targetSpeedLowKph": z.low / 100,
                                "targetSpeedHighKph": z.high / 100,
                            }
                            if z.parameter
                            else {"kind": "none"}
                        )
                        actual = {
                            "requestOpCode": z.request_opcode,
                            "resultCode": z.result_code,
                            "resultCodeName": names.get(
                                z.result_code, f"unknown_0x{z.result_code:02x}"
                            ),
                            "success": z.result_code == 1,
                            "parameter": p,
                            "issues": (["reserved_value"] if z.unknown_result else []),
                        }
                        ok = actual == x["expected"]
                    else:
                        outs.append(
                            {
                                "id": x["id"],
                                "category": cat,
                                "outcome": "unsupported",
                                "reason": "outside Python milestone",
                            }
                        )
                        continue
                    outs.append(_out(x["id"], cat, None, ok, "comparison mismatch"))
                except Exception as e:
                    outs.append(_out(x["id"], cat, None, False, type(e).__name__))
        vo = []
        for x in b["cases"]:
            if x["operation"] == "features":
                feature_raw = FeaturesRaw(x["machine"], x["target"])
                feature_decoded = decode_features_raw(bytes(x["expectedBytes"]))
                checks = [
                    feature_decoded == feature_raw,
                    encode_features_raw(feature_raw) == bytes(x["expectedBytes"]),
                ]
            else:
                range_raw = SupportedRangeRaw(
                    x["kind"],
                    x["minimum"],
                    x["maximum"],
                    x["increment"],
                    x["scaleDivisor"],
                    {
                        "speed": "km/h",
                        "inclination": "percent",
                        "resistance": "level",
                        "heartRate": "bpm",
                        "power": "watts",
                    }[x["kind"]],
                )
                range_decoded = decode_supported_range_raw(bytes(x["expectedBytes"]), x["kind"])
                checks = [
                    _raw_dict(range_decoded) == _raw_dict(range_raw),
                    encode_supported_range_raw(range_raw) == bytes(x["expectedBytes"]),
                ]
            vo += [
                _out(x["id"], x["operation"], n, ok, "mismatch")
                for n, ok in zip(("decode", "encode"), checks)
            ]
        co = []
        for x in c["requests"]:
            o = ControlFormatOptions(x.get("format", "signed16Tenths"))
            request_raw = ControlRequestRaw(x["decoded"]["opcode"], tuple(x["decoded"]["operands"]))
            co += [
                _out(
                    x["id"],
                    "request",
                    "decode",
                    decode_control_request_raw(bytes(x["bytes"]), o) == request_raw,
                    "mismatch",
                ),
                _out(
                    x["id"],
                    "request",
                    "encode",
                    encode_control_request_raw(request_raw, o) == bytes(x["bytes"]),
                    "mismatch",
                ),
            ]
        for x in c["responses"]:
            response_raw = ControlResponseRaw(
                **{
                    "".join("_" + q.lower() if q.isupper() else q for q in k).lstrip("_"): v
                    for k, v in x["decoded"].items()
                }
            )
            co.append(
                _out(
                    x["id"],
                    "response",
                    "decode",
                    decode_control_response_raw(bytes(x["bytes"])) == response_raw,
                    "mismatch",
                )
            )
            if x.get("encode", True):
                co.append(
                    _out(
                        x["id"],
                        "response",
                        "encode",
                        encode_control_response_raw(response_raw) == bytes(x["bytes"]),
                        "mismatch",
                    )
                )
        for x in c["invalid"]:
            try:
                decode_control_request_raw(
                    bytes(x["bytes"]), ControlFormatOptions(x.get("format", "signed16Tenths"))
                ) if x["operation"] == "request" else decode_control_response_raw(bytes(x["bytes"]))
                ok = False
            except RawCodecError as e:
                ok = e.code == x["error"]
            co.append(_out(x["id"], "invalid", "decode", ok, "wrong rejection"))
        io = []
        for x in fi["cases"]:
            opt = RangeFormatOptions((x.get("options") or {}).get("resistanceFormat", "uint8Whole"))
            io.append(
                _out(
                    x["id"],
                    "inspection",
                    None,
                    inspect_supported_range_raw(bytes(x["bytes"]), x["kind"], opt) == x["expected"],
                    "mismatch",
                )
            )
        compatibility_outcomes: list[dict[str, str]] = []
        for x in d["cases"]:
            if x["area"] != "range":
                measurement_option = MeasurementFormatOptions(
                    x["options"]["resistanceFormat"], x["options"]["treadmillPaceFormat"]
                )
                expected_measurement = measurement_expected(x["expected"])
                compatibility_outcomes.append(
                    _out(
                        x["id"],
                        "measurement",
                        "decode",
                        decode_measurement_raw(bytes(x["bytes"]), x["kind"], measurement_option)
                        == expected_measurement,
                        "measurement comparison mismatch",
                    )
                )
                if x.get("encode", True):
                    compatibility_outcomes.append(
                        _out(
                            x["id"],
                            "measurement",
                            "encode",
                            encode_measurement_raw(expected_measurement, measurement_option)
                            == bytes(x["bytes"]),
                            "measurement encoding mismatch",
                        )
                    )
                continue
            option = RangeFormatOptions(
                (x.get("options") or {}).get("resistanceFormat", "uint8Whole")
            )
            decoded = decode_supported_range_raw(bytes(x["bytes"]), x["kind"], option)
            raw = SupportedRangeRaw(
                x["kind"],
                x["expected"]["minimum"],
                x["expected"]["maximum"],
                x["expected"]["increment"],
                x["expected"]["scaleDivisor"],
                {0: "km/h", 1: "percent", 2: "level", 3: "bpm", 4: "watts"}[x["expected"]["unit"]],
            )
            compatibility_outcomes.extend(
                (
                    _out(
                        x["id"], "range", "decode", _raw_dict(decoded) == x["expected"], "mismatch"
                    ),
                    _out(
                        x["id"],
                        "range",
                        "encode",
                        encode_supported_range_raw(raw, option) == bytes(x["bytes"]),
                        "mismatch",
                    ),
                )
            )
        report.update(
            v1={
                "schemaVersion": a["schemaVersion"],
                "caseCounts": {
                    "total": sum(len(a[k]) for k in CATS),
                    "byCategory": {k: len(a[k]) for k in CATS},
                },
                "assertionCounts": {"total": len(outs), **_counts(outs)},
                "outcomes": outs,
                "sha256": _hashes(v1),
            },
            valuesV1={
                "schemaVersion": b["schemaVersion"],
                "caseCounts": {
                    "total": len(b["cases"]),
                    "byCategory": {
                        "features": sum(x["operation"] == "features" for x in b["cases"]),
                        "ranges": sum(x["operation"] != "features" for x in b["cases"]),
                    },
                },
                "assertionCounts": {"total": len(vo), **_counts(vo)},
                "outcomes": vo,
                "sha256": _hashes(values),
            },
            controlsV1={
                "schemaVersion": c["schemaVersion"],
                "caseCounts": {
                    "total": len(c["requests"]) + len(c["responses"]) + len(c["invalid"]),
                    "byCategory": {
                        "requests": len(c["requests"]),
                        "responses": len(c["responses"]),
                        "invalid": len(c["invalid"]),
                    },
                },
                "assertionCounts": {"total": len(co), **_counts(co)},
                "outcomes": co,
                "sha256": _hashes(controls),
            },
            inspectionV1={
                "schemaVersion": fi["schemaVersion"],
                "caseCounts": {"total": len(fi["cases"])},
                "assertionCounts": {"total": len(io), **_counts(io)},
                "outcomes": io,
                "sha256": {
                    str(inspect / "fixtures.json"): _sha(inspect / "fixtures.json"),
                    str(inspect / "README.md"): _sha(inspect / "README.md"),
                },
            },
            compatibilityV1={
                "schemaVersion": d["schemaVersion"],
                "caseCounts": {
                    "total": len(d["cases"]),
                    "byCategory": {
                        "ranges": sum(x["area"] == "range" for x in d["cases"]),
                        "measurements": sum(x["area"] == "measurement" for x in d["cases"]),
                    },
                },
                "assertionCounts": {
                    "total": len(compatibility_outcomes),
                    **_counts(compatibility_outcomes),
                },
                "outcomes": compatibility_outcomes,
                "sha256": _hashes(compat),
            },
        )
    except Exception as e:
        report["runnerErrors"].append({"reason": f"{type(e).__name__}: {e}"})
    expected_controls: set[tuple[str, str | None]] = cast(
        set[tuple[str, str | None]],
        (
            {(x["id"], direction) for x in c["requests"] for direction in ("decode", "encode")}
            | {(x["id"], "decode") for x in c["responses"]}
            | {(x["id"], "encode") for x in c["responses"] if x.get("encode", True)}
            | {(x["id"], "decode") for x in c["invalid"]}
            if "c" in locals()
            else set()
        ),
    )
    expected_values: set[tuple[str, str | None]] = cast(
        set[tuple[str, str | None]],
        (
            {(x["id"], direction) for x in b["cases"] for direction in ("decode", "encode")}
            if "b" in locals()
            else set()
        ),
    )
    expected_inspection: set[tuple[str, str | None]] = cast(
        set[tuple[str, str | None]],
        {(x["id"], None) for x in fi["cases"]} if "fi" in locals() else set(),
    )
    expected_compatibility: set[tuple[str, str | None]] = cast(
        set[tuple[str, str | None]],
        (
            {
                (x["id"], direction)
                for x in d["cases"]
                for direction in (("decode", "encode") if x.get("encode", True) else ("decode",))
            }
            if "d" in locals()
            else set()
        ),
    )
    report["runnerComplete"] = (
        not report["runnerErrors"]
        and all(
            report[s]["assertionCounts"]["failed"] == 0
            for s in ("v1", "valuesV1", "controlsV1", "inspectionV1", "compatibilityV1")
        )
        and _complete(report["controlsV1"]["outcomes"], expected_controls)
        and _complete(report["valuesV1"]["outcomes"], expected_values)
        and _complete(report["inspectionV1"]["outcomes"], expected_inspection)
        and _complete(report["compatibilityV1"]["outcomes"], expected_compatibility)
        and _complete(
            report["v1"]["outcomes"], {(x["id"], None) for category in CATS for x in a[category]}
        )
    )
    report["conformanceComplete"] = report["runnerComplete"] and all(
        report[section]["assertionCounts"][x] == 0
        for section in ("v1", "valuesV1", "controlsV1", "inspectionV1", "compatibilityV1")
        for x in ("unsupported", "skipped")
    )
    (PACKAGE / "build").mkdir(exist_ok=True)
    (PACKAGE / "build" / "verification-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


if __name__ == "__main__":
    raise SystemExit(0 if run()["runnerComplete"] else 1)
