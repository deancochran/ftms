from dataclasses import replace
from typing import Any

import pytest

from deancochran_ftms import (
    MeasurementRaw,
    RawCodecError,
    decode_measurement_raw,
    encode_measurement_raw,
    normalize_measurement,
)


@pytest.mark.parametrize("option", [0, False, [], {}, "bad", object()])
def test_reject_foreign_options(option: Any) -> None:
    raw = decode_measurement_raw(b"\x00\x00\x01\x00", 5)
    for call in (
        lambda: decode_measurement_raw(b"\x00\x00\x01\x00", 5, option),
        lambda: encode_measurement_raw(raw, option),
        lambda: normalize_measurement(raw, option),
    ):
        with pytest.raises(RawCodecError):
            call()


@pytest.mark.parametrize(
    "field",
    [
        "present",
        "unavailable",
        "more_data",
        "backward",
        "truncated",
        "trailing_bytes",
        "reserved_flags",
        "bytes_read",
    ],
)
@pytest.mark.parametrize("value", [True, -1, "0", 1.0])
def test_raw_metadata_is_plain_bounded_integer(field: str, value: Any) -> None:
    raw = decode_measurement_raw(b"\x00\x00\x01\x00", 5)
    with pytest.raises(RawCodecError):
        replace(raw, **{field: value})


def test_raw_values_are_immutable_and_wrong_models_rejected() -> None:
    with pytest.raises(RawCodecError):
        MeasurementRaw(0, 0, 1, 0, [0] * 30)  # type: ignore[arg-type]
    with pytest.raises(RawCodecError):
        encode_measurement_raw(None)  # type: ignore[arg-type]
    with pytest.raises(RawCodecError):
        normalize_measurement(None)  # type: ignore[arg-type]
