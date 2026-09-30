"""Independent literal/corpus checks for the native measurement and status codecs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deancochran_ftms import (
    MeasurementFormatOptions,
    MeasurementRaw,
    RawCodecError,
    TrainingStatusRaw,
    decode_machine_status_raw,
    decode_measurement_raw,
    decode_training_status_raw,
    encode_machine_status_raw,
    encode_measurement_raw,
    encode_training_status_raw,
    normalize_machine_status,
    normalize_measurement,
    normalize_training_status,
)

ROOT = Path(__file__).resolve().parents[3]


def test_measurement_literal_boundaries() -> None:
    assert decode_measurement_raw(bytes([65, 0, 255, 127]), 5).values[17] == 32767
    assert decode_measurement_raw(bytes([9, 0, 255, 127, 255, 127]), 0).unavailable == (1 << 3) | (
        1 << 4
    )
    assert encode_measurement_raw(MeasurementRaw(0, 0, 1, 0, (1234,) + (0,) * 29)) == bytes(
        [0, 0, 210, 4]
    )
    with pytest.raises(RawCodecError):
        encode_measurement_raw(MeasurementRaw(0, 0x2000, 1, 0, (1,) + (0,) * 29))


def test_measurement_directional_corpus() -> None:
    v = json.loads((ROOT / "shared/conformance/measurements/v1/vectors.json").read_text())
    for c in v["cases"]:
        if "error" in c["decoded"]:
            with pytest.raises(RawCodecError):
                decode_measurement_raw(bytes(c["bytes"]), c["kind"])
            continue
        e = c["decoded"]
        d = decode_measurement_raw(bytes(c["bytes"]), c["kind"])
        assert d == MeasurementRaw(
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
        ), c["id"]
        if c["encode"]:
            assert encode_measurement_raw(d) == bytes(c["bytes"]), c["id"]


def test_status_directional_corpus() -> None:
    v = json.loads((ROOT / "shared/conformance/statuses/v1/vectors.json").read_text())
    for c in v["machine"]:
        d = decode_machine_status_raw(bytes(c["bytes"]))
        e = c["decoded"]
        actual = {
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
        assert actual == e, c["id"]
        if c["encode"]:
            assert encode_machine_status_raw(d) == bytes(c["bytes"]), c["id"]
    for c in v["training"]:
        training = decode_training_status_raw(bytes(c["bytes"]))
        e = c["decoded"]
        training_actual: dict[str, object] = {
            "flags": training.flags,
            "code": training.code,
            "textOffset": training.text_offset,
            "textSize": training.text_size,
            "textPresent": training.text_present,
            "extendedString": training.extended_string,
            "reservedFlags": training.reserved_flags,
            "reservedValue": training.reserved_value,
            "invalidFlags": training.invalid_flags,
            "invalidUtf8": training.invalid_utf8,
            "truncated": training.truncated,
            "trailingBytes": training.trailing_bytes,
            "textHex": training.text.hex(),
        }
        assert training_actual == e, c["id"]
        if c["encode"]:
            assert encode_training_status_raw(training) == bytes(c["bytes"]), c["id"]


def test_measurement_compatibility_corpus() -> None:
    v = json.loads((ROOT / "shared/conformance/compatibility/v1/vectors.json").read_text())
    for c in v["cases"]:
        if c["area"] != "measurement":
            continue
        x = c["options"]
        o = MeasurementFormatOptions(x["resistanceFormat"], x["treadmillPaceFormat"])
        e = c["expected"]
        d = decode_measurement_raw(bytes(c["bytes"]), c["kind"], o)
        assert d == MeasurementRaw(
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
        ), c["id"]
        if c["encode"]:
            assert encode_measurement_raw(d, o) == bytes(c["bytes"]), c["id"]


def test_codec_v1_normalized_measurements_statuses_and_diagnostics() -> None:
    v = json.loads((ROOT / "shared/conformance/v1/vectors.json").read_text())
    kinds = {
        "00002acd": 0,
        "00002ace": 1,
        "00002acf": 2,
        "00002ad0": 3,
        "00002ad1": 4,
        "00002ad2": 5,
    }
    for c in v["measurements"]:
        kind = next(k for u, k in kinds.items() if c["characteristicUuid"].startswith(u))
        a = normalize_measurement(decode_measurement_raw(bytes(c["bytes"]), kind))
        for key, value in c["expectedMetrics"].items():
            assert a[key] == value, c["id"]
    for c in v["statuses"]:
        status_view = (
            normalize_training_status(decode_training_status_raw(bytes(c["bytes"])))
            if c["characteristicUuid"].startswith("00002ad3")
            else normalize_machine_status(decode_machine_status_raw(bytes(c["bytes"])))
        )
        assert status_view == c["expectedStatus"], c["id"]
    for c in v["diagnostics"]:
        if not any(c["characteristicUuid"].startswith(x) for x in kinds):
            continue
        kind = next(k for u, k in kinds.items() if c["characteristicUuid"].startswith(u))
        d = decode_measurement_raw(bytes(c["bytes"]), kind)
        a = normalize_measurement(d)
        assert bool(d.truncated) == c["expectedTruncated"], c["id"]
        for key, value in c.get("expectedMetrics", {}).items():
            assert a[key] == value, c["id"]


def test_training_encoder_rejects_invalid_utf8_and_diagnostics() -> None:
    with pytest.raises(RawCodecError):
        encode_training_status_raw(TrainingStatusRaw(1, 1, b"\xc3"))
    with pytest.raises(RawCodecError):
        encode_training_status_raw(decode_training_status_raw(bytes([1, 1, 0xC3])))
