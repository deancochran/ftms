#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import jsonschema

from deancochran_ftms import (
    MachineStatusRaw,
    MeasurementRaw,
    RawCodecError,
    TrainingStatusRaw,
    decode_machine_status_raw,
    decode_measurement_raw,
    decode_training_status_raw,
    encode_machine_status_raw,
    encode_measurement_raw,
    encode_training_status_raw,
)

P = Path(__file__).resolve().parents[1]
R = P.parents[1]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def machine_dict(d: MachineStatusRaw) -> dict[str, object]:
    return {
        "opcode": d.opcode,
        "action": d.action,
        "parameter": None
        if d.parameter is None
        else {"opcode": d.parameter[0], "operands": list(d.parameter[1])},
        "unknownOpcode": d.unknown_opcode,
        "reservedValue": d.reserved_value,
        "truncated": d.truncated,
        "trailingBytes": d.trailing_bytes,
    }


def training_dict(d: TrainingStatusRaw) -> dict[str, object]:
    return {
        "flags": d.flags,
        "code": d.code,
        "textOffset": d.text_offset,
        "textSize": d.text_size,
        "textPresent": d.text_present,
        "extendedString": d.extended_string,
        "reservedFlags": d.reserved_flags,
        "reservedValue": d.reserved_value,
        "invalidFlags": d.invalid_flags,
        "invalidUtf8": d.invalid_utf8,
        "truncated": d.truncated,
        "trailingBytes": d.trailing_bytes,
        "textHex": d.text.hex(),
    }


def expected_machine(e: dict[str, Any]) -> MachineStatusRaw:
    parameter = e["parameter"]
    return MachineStatusRaw(
        e["opcode"],
        e["action"],
        None if parameter is None else (parameter["opcode"], tuple(parameter["operands"])),
        e["unknownOpcode"],
        e["reservedValue"],
        e["truncated"],
        e["trailingBytes"],
    )


def expected_training(e: dict[str, Any]) -> TrainingStatusRaw:
    return TrainingStatusRaw(
        e["flags"],
        e["code"],
        bytes.fromhex(e["textHex"]),
        e["textOffset"],
        e["textSize"],
        e["textPresent"],
        e["extendedString"],
        e["reservedFlags"],
        e["reservedValue"],
        e["invalidFlags"],
        e["invalidUtf8"],
        e["truncated"],
        e["trailingBytes"],
    )


def main() -> int:
    report: dict[str, Any] = {
        "sourceCommit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=R, text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=R, text=True).strip()
        ),
        "runnerErrors": [],
        "corpora": {},
    }
    try:
        for name in ("measurements", "statuses"):
            d = R / "shared/conformance" / name / "v1"
            schema = json.loads((d / "schema.json").read_text())
            v = json.loads((d / "vectors.json").read_text())
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.validate(v, schema)
            outs = []
            cases = v["cases"] if name == "measurements" else v["machine"] + v["training"]
            ids = [x["id"] for x in cases]
            if len(ids) != len(set(ids)):
                raise ValueError("duplicate ids")
            for c in cases:
                if name == "measurements":
                    try:
                        d0 = decode_measurement_raw(bytes(c["bytes"]), c["kind"])
                        e = c["decoded"]
                        ok = "error" not in e and d0 == MeasurementRaw(
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
                        outs.append(
                            {
                                "id": c["id"],
                                "direction": "decode",
                                "outcome": "passed" if ok else "failed",
                            }
                        )
                    except RawCodecError as error:
                        outs.append(
                            {
                                "id": c["id"],
                                "direction": "decode",
                                "outcome": "passed"
                                if c["decoded"].get("error") == 3
                                and error.code == "kind"
                                or c["decoded"].get("error") == 2
                                and error.code == "length"
                                else "failed",
                            }
                        )
                    if c["encode"]:
                        e = c["decoded"]
                        m = MeasurementRaw(
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
                        outs.append(
                            {
                                "id": c["id"],
                                "direction": "encode",
                                "outcome": "passed"
                                if encode_measurement_raw(m) == bytes(c["bytes"])
                                else "failed",
                            }
                        )
                else:
                    if c["operation"] == "machine":
                        machine_decoded = decode_machine_status_raw(bytes(c["bytes"]))
                        encoded = (
                            encode_machine_status_raw(expected_machine(c["decoded"]))
                            if c["encode"]
                            else b""
                        )
                    else:
                        training_decoded = decode_training_status_raw(bytes(c["bytes"]))
                        encoded = (
                            encode_training_status_raw(expected_training(c["decoded"]))
                            if c["encode"]
                            else b""
                        )
                    expected = c["decoded"]
                    actual = (
                        machine_dict(machine_decoded)
                        if c["operation"] == "machine"
                        else training_dict(training_decoded)
                    )
                    outs.append(
                        {
                            "id": c["id"],
                            "direction": "decode",
                            "outcome": "passed" if actual == expected else "failed",
                        }
                    )
                    if c["encode"]:
                        outs.append(
                            {
                                "id": c["id"],
                                "direction": "encode",
                                "outcome": "passed" if encoded == bytes(c["bytes"]) else "failed",
                            }
                        )
            expected_directions = {
                (case["id"], direction)
                for case in cases
                for direction in (("decode", "encode") if case["encode"] else ("decode",))
            }
            actual_directions = [(out["id"], out["direction"]) for out in outs]
            if (
                not expected_directions
                or set(actual_directions) != expected_directions
                or len(actual_directions) != len(expected_directions)
            ):
                raise ValueError(f"incomplete directional accounting: {name}")
            for out in outs:
                out["reason"] = (
                    ""
                    if out["outcome"] == "passed"
                    else "actual result differs from canonical fixture"
                )
            report["corpora"][name] = {
                "schemaVersion": v["schemaVersion"],
                "caseCount": len(cases),
                "assertionCount": len(outs),
                "byCategory": (
                    {"measurement": len(cases)}
                    if name == "measurements"
                    else {"machine": len(v["machine"]), "training": len(v["training"])}
                ),
                "counts": {
                    status: sum(o["outcome"] == status for o in outs)
                    for status in ("passed", "failed", "unsupported", "skipped")
                },
                "outcomes": outs,
                "sha256": {
                    str(x.relative_to(R)): sha(x)
                    for x in (d / "schema.json", d / "vectors.json", d.parent / "README.md")
                },
            }
    except Exception as e:
        report["runnerErrors"].append(f"{type(e).__name__}: {e}")
    report["complete"] = (
        not report["runnerErrors"]
        and set(report["corpora"]) == {"measurements", "statuses"}
        and all(x["outcome"] == "passed" for c in report["corpora"].values() for x in c["outcomes"])
    )
    (P / "build").mkdir(exist_ok=True)
    (P / "build" / "measurement-status-verification-report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "complete": report["complete"],
                "report": str(P / "build" / "measurement-status-verification-report.json"),
            }
        )
    )
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
