"""UUID-dispatched measurement convenience API regression coverage."""

from __future__ import annotations

import json
import re
from pathlib import Path

from deancochran_ftms import MeasurementFormatOptions, decode_measurement

ROOT = Path(__file__).parents[3]


def test_universal_decoder_projects_each_measurement_family_from_canonical_vectors() -> None:
    vectors = json.loads((ROOT / "shared/conformance/v1/vectors.json").read_text())["measurements"]
    seen: set[str] = set()
    for vector in vectors:
        uuid = vector["characteristicUuid"]
        if uuid in seen:
            continue
        seen.add(uuid)
        result = decode_measurement(uuid, bytes(vector["bytes"]))
        assert result.known and result.measurement is not None
        measurement = result.measurement
        assert measurement.raw.kind == len(seen) - 1
        assert isinstance(measurement.raw.values, tuple)
        assert measurement.raw.flags == int.from_bytes(
            bytes(vector["bytes"])[: 3 if uuid.lower().startswith("00002ace-") else 2],
            "little",
        )
        for name, expected in vector["expectedMetrics"].items():
            attribute = re.sub(r"(?<!^)([A-Z])", r"_\1", name).lower()
            attribute = attribute.replace("per500m", "per_500m")
            assert getattr(measurement.metrics, attribute) == expected
        if len(seen) == 6:
            break
    assert len(seen) == 6


def test_universal_decoder_retains_selected_format_and_raw_diagnostics() -> None:
    legacy = decode_measurement(
        "00002acd-0000-1000-8000-00805f9b34fb",
        b"\x21\x00\x00",
        MeasurementFormatOptions(treadmill_pace_format="uint8Legacy"),
    )
    assert legacy.measurement is not None
    assert legacy.measurement.format.treadmill_pace_format == "uint8Legacy"
    assert legacy.measurement.raw.values[7] == 0  # zero is raw evidence, not absent.
    assert legacy.measurement.metrics.instantaneous_pace_seconds_per_500m is None

    truncated = decode_measurement("00002ad2-0000-1000-8000-00805f9b34fb", b"\xfe\x1f")
    assert truncated.measurement is not None
    assert truncated.measurement.raw.truncated == 1
    assert truncated.measurement.diagnostics.truncated
    assert truncated.measurement.diagnostics.bytes_read == 2

    unavailable = decode_measurement(
        "00002ad2-0000-1000-8000-00805f9b34fb", b"\x01\x01\xff\xff\x02\x00\x03"
    )
    assert unavailable.measurement is not None
    assert unavailable.measurement.raw.unavailable & (1 << 9)
    assert unavailable.measurement.metrics.energy_kcal is None


def test_universal_decoder_accepts_documented_aliases_and_rejects_invalid_uuids() -> None:
    for uuid in (
        "00002acd-0000-1000-8000-00805F9B34FB",
        "00002ACD00001000800000805F9B34FB",
        "2AcD",
        "0x2aCd",
    ):
        result = decode_measurement(uuid, b"\x00\x00\x00\x00")
        assert result.known and result.measurement is not None

    for uuid in (
        "00002acd0000-1000-8000-00805f9b34fb",
        "00002acd_0000_1000_8000_00805f9b34fb",
        "00002acd-0000-1000-8000-00805f9b34f",
        "0x2acd0",
        "12345678123456781234567812345678",
        "00002acc00001000800000805f9b34fb",
    ):
        result = decode_measurement(uuid, b"")
        assert not result.known
        assert result.measurement is None
        assert result.unsupported_uuid == uuid
