"""Strict raw and normalized FTMS supported-range codecs and inspection."""

from __future__ import annotations

import struct
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal, cast

from ._binary import immutable_bytes
from ._errors import RawCodecError

RangeKind = Literal["speed", "inclination", "resistance", "heartRate", "power"]
RangeProfile = Literal[
    "uint16Hundredths", "signed16Tenths", "uint8Whole", "uint8Bpm", "signed16Watts"
]
_LAYOUT = {
    "speed": ("uint16Hundredths", "<HHH", 100, "km/h"),
    "inclination": ("signed16Tenths", "<hhH", 10, "percent"),
    "resistance": ("uint8Whole", "<BBB", 1, "level"),
    "heartRate": ("uint8Bpm", "<BBB", 1, "bpm"),
    "power": ("signed16Watts", "<hhH", 1, "watts"),
}


@dataclass(frozen=True, slots=True)
class SupportedRangeRaw:
    kind: RangeKind
    minimum: int
    maximum: int
    increment: int
    scale_divisor: int
    unit: str


@dataclass(frozen=True, slots=True)
class SupportedRange:
    kind: RangeKind
    minimum: float
    maximum: float
    increment: float
    unit: str


@dataclass(frozen=True, slots=True)
class RangeFormatOptions:
    resistance_format: Literal["uint8Whole", "signed16Tenths"] = "uint8Whole"


def _layout(
    kind: object, options: RangeFormatOptions | None = None
) -> tuple[RangeProfile, str, int, str]:
    if not isinstance(kind, str) or kind not in _LAYOUT:
        raise RawCodecError("kind", "Unknown supported range kind")
    if options is not None and not isinstance(options, RangeFormatOptions):
        raise RawCodecError("kind", "Range options must be RangeFormatOptions")
    if options is not None and options.resistance_format not in ("uint8Whole", "signed16Tenths"):
        raise RawCodecError("kind", "Unsupported resistance range format")
    if kind != "resistance" and options is not None and options.resistance_format != "uint8Whole":
        raise RawCodecError("kind", "Resistance range format applies only to resistance")
    if kind == "resistance" and options and options.resistance_format == "signed16Tenths":
        return ("signed16Tenths", "<hhH", 10, "level")
    return cast(tuple[RangeProfile, str, int, str], _LAYOUT[cast(RangeKind, kind)])


def _validate(raw: SupportedRangeRaw, layout: tuple[str, str, int, str]) -> None:
    if not isinstance(raw, SupportedRangeRaw):
        raise RawCodecError("kind", "SupportedRangeRaw value is required")
    if (
        type(raw.scale_divisor) is not int
        or raw.scale_divisor != layout[2]
        or raw.unit != layout[3]
    ):
        raise RawCodecError("kind", "range unit/divisor does not match selected format")
    if any(type(x) is not int for x in (raw.minimum, raw.maximum, raw.increment)):
        raise RawCodecError("range", "range values must be integers")
    if raw.increment <= 0 or raw.minimum > raw.maximum:
        raise RawCodecError("range", "range increment must be positive and bounds ordered")
    try:
        struct.pack(layout[1], raw.minimum, raw.maximum, raw.increment)
    except struct.error as e:
        raise RawCodecError("range", "range values are outside selected widths") from e


def decode_supported_range_raw(
    data: bytes | bytearray | memoryview, kind: RangeKind, options: RangeFormatOptions | None = None
) -> SupportedRangeRaw:
    profile, fmt, divisor, unit = _layout(kind, options)
    b = immutable_bytes(data)
    size = struct.calcsize(fmt)
    if len(b) != size:
        raise RawCodecError("length", f"{kind} range requires exactly {size} bytes")
    minimum, maximum, increment = struct.unpack(fmt, b)
    raw = SupportedRangeRaw(kind, minimum, maximum, increment, divisor, unit)
    _validate(raw, (profile, fmt, divisor, unit))
    return raw


def encode_supported_range_raw(
    raw: SupportedRangeRaw, options: RangeFormatOptions | None = None
) -> bytes:
    if not isinstance(raw, SupportedRangeRaw):
        raise RawCodecError("kind", "SupportedRangeRaw value is required")
    layout = _layout(raw.kind, options)
    _validate(raw, layout)
    return struct.pack(layout[1], raw.minimum, raw.maximum, raw.increment)


def decode_supported_range(
    data: bytes | bytearray | memoryview, kind: RangeKind, options: RangeFormatOptions | None = None
) -> SupportedRange:
    r = decode_supported_range_raw(data, kind, options)
    return SupportedRange(
        r.kind,
        r.minimum / r.scale_divisor,
        r.maximum / r.scale_divisor,
        r.increment / r.scale_divisor,
        r.unit,
    )


def inspect_supported_range_raw(
    data: bytes | bytearray | memoryview, kind: RangeKind, options: RangeFormatOptions | None = None
) -> dict[str, object]:
    b = immutable_bytes(data)
    selected = _layout(kind, options)
    candidates = []
    layouts = (
        [selected]
        if kind != "resistance"
        else [_LAYOUT["resistance"], ("signed16Tenths", "<hhH", 10, "level")]
    )
    for layout in layouts:
        profile, fmt, divisor, unit = layout
        size = struct.calcsize(fmt)
        try:
            if len(b) != size:
                raise RawCodecError("length", "wrong length")
            x = decode_supported_range_raw(
                b,
                kind,
                RangeFormatOptions(cast(Literal["uint8Whole", "signed16Tenths"], profile))
                if kind == "resistance"
                else None,
            )
            value = {
                "kind": x.kind,
                "minimum": x.minimum,
                "maximum": x.maximum,
                "increment": x.increment,
                "scaleDivisor": x.scale_divisor,
                "unit": {"speed": 0, "inclination": 1, "resistance": 2, "heartRate": 3, "power": 4}[
                    kind
                ],
            }
            status = "valid"
        except RawCodecError as e:
            value = None
            status = e.code
        candidates.append(
            {"profile": profile, "expectedLength": size, "status": status, "value": value}
        )
    chosen = (
        candidates[0]
        if kind != "resistance"
        else next(x for x in candidates if x["profile"] == selected[0])
    )
    return {
        "selectedProfile": selected[0],
        "actualLength": len(b),
        "expectedLength": chosen["expectedLength"],
        "status": chosen["status"],
        "value": deepcopy(chosen["value"]),
        "candidates": candidates,
    }
