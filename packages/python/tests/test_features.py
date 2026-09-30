from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from deancochran_ftms import (
    FeaturesRaw,
    RawCodecError,
    decode_features,
    decode_features_raw,
    encode_features_raw,
)


def test_raw_round_trip_preserves_reserved_bits_and_is_little_endian() -> None:
    raw = FeaturesRaw(0x80FF_FDEF, 0xF000_0001)
    encoded = encode_features_raw(raw)
    assert encoded == b"\xef\xfd\xff\x80\x01\x00\x00\xf0"
    assert decode_features_raw(encoded) == raw


def test_normalized_bits_aliases_and_immutable_result() -> None:
    result = decode_features(
        encode_features_raw(FeaturesRaw(1 << 16, (1 << 2) | (1 << 3) | (1 << 13)))
    )
    assert result.ok and result.value is not None
    assert result.value.user_data_retention_supported
    assert (
        result.value.supports_erg and result.value.supports_sim and result.value.supports_resistance
    )
    with pytest.raises((FrozenInstanceError, TypeError)):
        result.value.power_target_setting_supported = False  # type: ignore[misc]


@pytest.mark.parametrize("size", [0, 7, 9])
def test_exact_length_including_trailing_bytes(size: int) -> None:
    data = bytes(size)
    result = decode_features(data)
    assert not result.ok and result.diagnostic is not None
    assert result.diagnostic.code == "length" and result.diagnostic.expected == 8
    with pytest.raises(RawCodecError) as error:
        decode_features_raw(data)
    assert error.value.code == "length"


@pytest.mark.parametrize("word", [-1, 0x1_0000_0000, True, 1.0])
def test_raw_word_bounds_and_bool_rejection(word: object) -> None:
    with pytest.raises(RawCodecError) as error:
        encode_features_raw(FeaturesRaw(word, 0))  # type: ignore[arg-type]
    assert error.value.code == "range"


def test_input_kinds_and_retained_evidence() -> None:
    source = bytearray(encode_features_raw(FeaturesRaw(1, 2)))
    assert decode_features_raw(source) == FeaturesRaw(1, 2)
    source[0] = 0
    assert decode_features_raw(
        memoryview(bytes(encode_features_raw(FeaturesRaw(1, 2))))
    ) == FeaturesRaw(1, 2)
    for invalid in (None, memoryview(bytearray(16))[::2]):
        with pytest.raises(RawCodecError) as error:
            decode_features_raw(invalid)  # type: ignore[arg-type]
        assert error.value.code == "kind"
