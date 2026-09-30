"""Focused status normalization and strict raw-encoding checks."""

from __future__ import annotations

import pytest

from deancochran_ftms import (
    MachineStatusRaw,
    RawCodecError,
    TrainingStatusRaw,
    decode_machine_status_raw,
    decode_training_status_raw,
    encode_machine_status_raw,
    encode_training_status_raw,
    normalize_machine_status,
    normalize_training_status,
)


@pytest.mark.parametrize(
    ("payload", "label", "details"),
    [
        (b"\x01", "reset", {"kind": "none"}),
        (b"\x02\x01", "stopped_or_paused_by_user", {"kind": "stop_pause", "action": "stop"}),
        (b"\x03", "stopped_by_safety_key", {"kind": "none"}),
        (b"\x04", "started_or_resumed_by_user", {"kind": "none"}),
        (b"\x05\xd2\x04", "target_speed_changed", {"kind": "speed", "speedKph": 12.34}),
        (
            b"\x06\xf4\xff",
            "target_inclination_changed",
            {"kind": "inclination", "inclinationPercent": -1.2},
        ),
        (
            b"\x07\xf4\xff",
            "target_resistance_changed",
            {"kind": "resistance", "resistanceLevel": -1.2},
        ),
        (b"\x08\x9c\xff", "target_power_changed", {"kind": "power", "powerWatts": -100}),
        (b"\x09\x96", "target_heart_rate_changed", {"kind": "heart_rate", "heartRateBpm": 150}),
        (
            b"\x0a\xf4\x01",
            "targeted_expended_energy_changed",
            {"kind": "energy", "energyKcal": 500},
        ),
        (b"\x0b\x58\x02", "targeted_steps_changed", {"kind": "steps", "steps": 600}),
        (b"\x0c\xbc\x02", "targeted_strides_changed", {"kind": "strides", "strides": 700}),
        (
            b"\x0d\x03\x02\x01",
            "targeted_distance_changed",
            {"kind": "distance", "distanceMeters": 0x010203},
        ),
        (
            b"\x0e\x10\x0e",
            "targeted_training_time_changed",
            {"kind": "training_time", "seconds": 3600},
        ),
        (
            b"\x0f\x0a\0\x14\0",
            "targeted_time_two_hr_zones_changed",
            {"kind": "hr_zones", "seconds": [10, 20]},
        ),
        (
            b"\x10\x0a\0\x14\0\x1e\0",
            "targeted_time_three_hr_zones_changed",
            {"kind": "hr_zones", "seconds": [10, 20, 30]},
        ),
        (
            b"\x11\x0a\0\x14\0\x1e\0\x28\0\x32\0",
            "targeted_time_five_hr_zones_changed",
            {"kind": "hr_zones", "seconds": [10, 20, 30, 40, 50]},
        ),
        (
            b"\x12\xe8\x03\xfa\0\x0a\x14",
            "indoor_bike_simulation_parameters_changed",
            {
                "kind": "simulation",
                "windSpeedMps": 1,
                "gradePercent": 2.5,
                "crr": 0.001,
                "cwKgPerM": 0.2,
            },
        ),
        (
            b"\x13\x08\x52",
            "wheel_circumference_changed",
            {"kind": "wheel_circumference", "circumferenceMm": 2100},
        ),
        (b"\x14\x02", "spin_down_status", {"kind": "spin_down", "status": "success"}),
        (b"\x15\xb4\0", "targeted_cadence_changed", {"kind": "cadence", "cadenceRpm": 90}),
        (b"\xff", "control_permission_lost", {"kind": "none"}),
    ],
)
def test_normalize_every_known_machine_opcode(
    payload: bytes, label: str, details: dict[str, object]
) -> None:
    normalized = normalize_machine_status(decode_machine_status_raw(payload))
    assert normalized == {"code": payload[0], "label": label, "details": details}


def test_machine_encoder_rejects_ignored_fields_and_all_numeric_overflows() -> None:
    with pytest.raises(RawCodecError) as action_error:
        encode_machine_status_raw(MachineStatusRaw(1, action=1))
    assert action_error.value.code == "range"
    with pytest.raises(RawCodecError) as parameter_error:
        encode_machine_status_raw(MachineStatusRaw(1, parameter=(2, (1,))))
    assert parameter_error.value.code == "range"

    for raw in (
        MachineStatusRaw(5, parameter=(2, (65536,))),
        MachineStatusRaw(6, parameter=(3, (-32769,))),
        MachineStatusRaw(9, parameter=(6, (256,))),
        MachineStatusRaw(13, parameter=(12, (0x1000000,))),
        MachineStatusRaw(18, parameter=(17, (32768, 0, 0, 0))),
        MachineStatusRaw(18, parameter=(17, (0, 0, 256, 0))),
    ):
        with pytest.raises(RawCodecError) as error:
            encode_machine_status_raw(raw)
        assert error.value.code == "range"
    with pytest.raises(RawCodecError) as bool_error:
        MachineStatusRaw(15, parameter=(14, (True, 1)))
    assert bool_error.value.code == "range"


def test_training_decoder_and_normalizer_preserve_invalid_utf8_semantics() -> None:
    raw = decode_training_status_raw(b"\x03\x0d\xc3")
    assert raw.invalid_utf8 == 1
    assert normalize_training_status(raw) == {
        "code": 13,
        "label": "manual_mode",
        "details": {
            "kind": "training_status",
            "flags": 3,
            "stringPresent": True,
            "extendedStringPresent": True,
            "trainingStatusString": "�",
        },
    }
    assert normalize_training_status(decode_training_status_raw(b"\x01")) == {
        "code": None,
        "label": "unknown",
        "details": None,
    }
    assert normalize_training_status(decode_training_status_raw(b"\0\x10"))["label"] == "reserved"


@pytest.mark.parametrize(
    "raw",
    [
        TrainingStatusRaw(1, 1, b"x", text_offset=0, text_size=1, text_present=1),
        TrainingStatusRaw(1, 1, b"x", text_offset=2, text_size=0, text_present=1),
        TrainingStatusRaw(1, 1, b"x", text_offset=2, text_size=1, text_present=0),
        TrainingStatusRaw(
            1, 1, b"x", text_offset=2, text_size=1, text_present=1, extended_string=1
        ),
        TrainingStatusRaw(0, 1, b"", extended_string=1),
    ],
)
def test_training_encoder_uses_authoritative_flags_code_text(raw: TrainingStatusRaw) -> None:
    assert encode_training_status_raw(raw) == bytes((raw.flags, raw.code)) + raw.text


def test_training_encoder_accepts_default_decoder_metadata() -> None:
    assert encode_training_status_raw(TrainingStatusRaw(1, 1, b"x")) == b"\x01\x01x"
    assert encode_training_status_raw(TrainingStatusRaw(3, 1, b"x")) == b"\x03\x01x"
    with pytest.raises(RawCodecError):
        encode_training_status_raw(TrainingStatusRaw(1, 1, b"\xc3"))


@pytest.mark.parametrize(
    "raw",
    [
        MachineStatusRaw(5),
        MachineStatusRaw(5, parameter=(2, ())),
        MachineStatusRaw(5, parameter=(3, (1,))),
        MachineStatusRaw(5, parameter=(2, (65536,))),
    ],
)
def test_machine_normalizer_rejects_malformed_constructed_parameters(raw: MachineStatusRaw) -> None:
    with pytest.raises(RawCodecError):
        normalize_machine_status(raw)


@pytest.mark.parametrize("value", [None, "\x01", [1], 1])
def test_decoders_accept_only_byte_containers(value: object) -> None:
    for decoder in (decode_machine_status_raw, decode_training_status_raw):
        with pytest.raises(RawCodecError) as error:
            decoder(value)
        assert error.value.code == "kind"
    assert decode_machine_status_raw(bytearray(b"\x01")).opcode == 1
    assert decode_training_status_raw(memoryview(b"\0\x01")).code == 1
