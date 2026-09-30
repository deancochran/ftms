from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from deancochran_ftms import (
    ControlFormatOptions,
    ControlRequestRaw,
    ControlResponseRaw,
    RangeFormatOptions,
    RawCodecError,
    SupportedRangeRaw,
    decode_control_request_raw,
    decode_control_response_raw,
    decode_supported_range,
    decode_supported_range_raw,
    encode_control_request_raw,
    encode_control_response_raw,
    encode_supported_range_raw,
    inspect_supported_range_raw,
)


def assert_error(code: str, callback: Callable[[], object]) -> None:
    with pytest.raises(RawCodecError) as error:
        callback()
    assert error.value.code == code


@pytest.mark.parametrize(
    ("kind", "payload", "minimum", "maximum", "increment"),
    [
        ("speed", bytes([0, 0, 255, 255, 1, 0]), 0, 65535, 1),
        ("inclination", bytes([0, 128, 255, 127, 255, 255]), -32768, 32767, 65535),
        ("resistance", bytes([0, 255, 1]), 0, 255, 1),
        ("heartRate", bytes([0, 255, 1]), 0, 255, 1),
        ("power", bytes([0, 128, 255, 127, 255, 255]), -32768, 32767, 65535),
    ],
)
def test_range_wire_boundaries(
    kind: str, payload: bytes, minimum: int, maximum: int, increment: int
) -> None:
    value = decode_supported_range_raw(payload, kind)  # type: ignore[arg-type]
    assert (value.minimum, value.maximum, value.increment) == (minimum, maximum, increment)
    assert encode_supported_range_raw(value) == payload


def test_range_rejects_reversed_bounds_and_zero_increment() -> None:
    assert_error(
        "range", lambda: decode_supported_range_raw(bytes([10, 0, 9, 0, 1, 0]), "inclination")
    )
    assert_error("range", lambda: decode_supported_range_raw(bytes([1, 2, 0]), "resistance"))


@pytest.mark.parametrize("value", [True, False, 1.0, "1"])
def test_range_rejects_non_integer_raw_values(value: object) -> None:
    raw = SupportedRangeRaw("speed", value, 2, 1, 100, "km/h")  # type: ignore[arg-type]
    assert_error("range", lambda: encode_supported_range_raw(raw))


def test_range_rejects_bad_options_and_formats_and_is_immutable() -> None:
    raw = SupportedRangeRaw("resistance", 0, 10, 1, 1, "level")
    assert_error(
        "kind", lambda: encode_supported_range_raw(raw, cast(RangeFormatOptions, object()))
    )
    assert_error(
        "kind", lambda: encode_supported_range_raw(raw, RangeFormatOptions("signed16Tenths"))
    )
    with pytest.raises(FrozenInstanceError):
        raw.minimum = 3  # type: ignore[misc]


def test_inspection_candidates_are_ordered_selected_and_immutable() -> None:
    report = inspect_supported_range_raw(
        bytes([1, 100, 1]), "resistance", RangeFormatOptions("signed16Tenths")
    )
    assert report["selectedProfile"] == "signed16Tenths"
    assert report["status"] == "length"
    candidates = report["candidates"]
    assert isinstance(candidates, list)
    assert [item["profile"] for item in candidates] == ["uint8Whole", "signed16Tenths"]
    assert candidates[0]["status"] == "valid"
    # Returned report is detached from caller-owned input bytes.
    source = bytearray([1, 100, 1])
    before = inspect_supported_range_raw(source, "resistance")
    source[0] = 99
    assert before["value"] == {
        "kind": "resistance",
        "minimum": 1,
        "maximum": 100,
        "increment": 1,
        "scaleDivisor": 1,
        "unit": 2,
    }


def test_control_raw_boundaries_options_and_bool_rejection() -> None:
    assert encode_control_request_raw(ControlRequestRaw(12, (0xFFFFFF,))) == bytes(
        [12, 255, 255, 255]
    )
    assert encode_control_request_raw(ControlRequestRaw(3, (-32768,))) == bytes([3, 0, 128])
    assert decode_control_request_raw(
        bytes([4, 255]), ControlFormatOptions("uint8Tenths")
    ).operands == (255,)
    assert_error(
        "range",
        lambda: encode_control_request_raw(
            ControlRequestRaw(4, (-1,)), ControlFormatOptions("uint8Tenths")
        ),
    )
    assert_error("range", lambda: encode_control_request_raw(ControlRequestRaw(2, (True,))))
    assert_error(
        "kind", lambda: decode_control_request_raw(bytes([0]), cast(ControlFormatOptions, object()))
    )


def test_control_request_immutability_and_malformed_inputs() -> None:
    request = decode_control_request_raw(bytes([17, 0, 128, 255, 127, 0, 255]))
    assert request.operands == (-32768, 32767, 0, 255)
    with pytest.raises(FrozenInstanceError):
        request.opcode = 1  # type: ignore[misc]
    assert_error("length", lambda: decode_control_request_raw(bytes([2, 1])))
    assert_error("range", lambda: decode_control_request_raw(bytes([8, 0])))
    assert_error("kind", lambda: decode_control_request_raw(bytes([255])))


def test_response_invariants_unknowns_and_spin_down() -> None:
    spin = decode_control_response_raw(bytes([128, 19, 1, 100, 0, 200, 0]))
    assert spin == ControlResponseRaw(19, 1, 1, 100, 200)
    assert encode_control_response_raw(spin) == bytes([128, 19, 1, 100, 0, 200, 0])
    unknown = decode_control_response_raw(bytes([128, 250, 99]))
    assert (unknown.unknown_request, unknown.unknown_result) == (1, 1)
    assert_error("range", lambda: encode_control_response_raw(unknown))
    assert_error("range", lambda: encode_control_response_raw(ControlResponseRaw(19, 1, 0, 1, 0)))
    assert_error("length", lambda: decode_control_response_raw(bytes([128, 19, 1, 1])))
    assert_error("kind", lambda: decode_control_response_raw(bytes([129, 0, 1])))


@pytest.mark.parametrize("profile", ["invalid", None, True])
def test_invalid_range_profile_runtime_validation(profile: object) -> None:
    options = RangeFormatOptions(profile)  # type: ignore[arg-type]
    raw = SupportedRangeRaw("resistance", 0, 100, 1, 1, "level")
    assert_error("kind", lambda: encode_supported_range_raw(raw, options))
    for decode in (decode_supported_range_raw, decode_supported_range, inspect_supported_range_raw):
        assert_error("kind", lambda: decode(b"\x00\x64\x01", "resistance", options))


def test_resistance_range_profile_not_applied_to_other_kinds() -> None:
    options = RangeFormatOptions("signed16Tenths")
    raw = SupportedRangeRaw("speed", 0, 100, 1, 100, "km/h")
    assert_error("kind", lambda: encode_supported_range_raw(raw, options))
    for decode in (decode_supported_range_raw, decode_supported_range, inspect_supported_range_raw):
        assert_error("kind", lambda: decode(b"\x00\x00\x64\x00\x01\x00", "speed", options))
    # Control options have their own scope and may accompany unrelated opcodes.
    assert (
        encode_control_request_raw(ControlRequestRaw(0, ()), ControlFormatOptions("uint8Tenths"))
        == b"\x00"
    )


@pytest.mark.parametrize("value", [None, object(), []])
def test_range_wrong_runtime_types(value: object) -> None:
    assert_error("kind", lambda: encode_supported_range_raw(value))  # type: ignore[arg-type]
    assert_error("kind", lambda: decode_supported_range_raw(b"", value))  # type: ignore[arg-type]


@pytest.mark.parametrize("divisor", [True, 1.0])
def test_range_divisor_is_plain_integer(divisor: object) -> None:
    raw = SupportedRangeRaw("resistance", 0, 100, 1, divisor, "level")  # type: ignore[arg-type]
    assert_error("kind", lambda: encode_supported_range_raw(raw))


def test_inspection_selected_value_is_not_candidate_alias() -> None:
    report = inspect_supported_range_raw(b"\x00\x64\x01", "resistance")
    value = report["value"]
    candidates = report["candidates"]
    assert isinstance(value, dict) and isinstance(candidates, list)
    value["minimum"] = 99
    assert candidates[0]["value"]["minimum"] == 0
