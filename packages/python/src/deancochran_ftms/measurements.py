"""Raw, transport-independent FTMS measurement codecs."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ._binary import immutable_bytes
from ._errors import RawCodecError

FIELD_ORDER = (
    "speed",
    "averageSpeed",
    "distance",
    "inclination",
    "rampAngle",
    "positiveElevation",
    "negativeElevation",
    "instantaneousPace",
    "averagePace",
    "energy",
    "energyPerHour",
    "energyPerMinute",
    "heartRate",
    "met",
    "elapsed",
    "remaining",
    "force",
    "power",
    "stepRate",
    "averageStepRate",
    "strideCount",
    "resistance",
    "averagePower",
    "floorCount",
    "stepCount",
    "strokeRate",
    "strokeCount",
    "averageStrokeRate",
    "cadence",
    "averageCadence",
)
D = {
    0: (
        2,
        0x1FFF,
        (
            (0, 2, 0, 0, 0),
            (1, 2, 1, 0, 0),
            (2, 3, 2, 0, 0),
            (3, 2, 3, 1, 1),
            (3, 2, 4, 1, 1),
            (4, 2, 5, 0, 0),
            (4, 2, 6, 0, 0),
            (5, 2, 7, 0, 0),
            (6, 2, 8, 0, 0),
            (7, 2, 9, 0, 1),
            (7, 2, 10, 0, 1),
            (7, 1, 11, 0, 1),
            (8, 1, 12, 0, 0),
            (9, 1, 13, 0, 0),
            (10, 2, 14, 0, 0),
            (11, 2, 15, 0, 0),
            (12, 2, 16, 1, 1),
            (12, 2, 17, 1, 1),
        ),
    ),
    1: (
        3,
        0xFFFF,
        (
            (0, 2, 0, 0, 0),
            (1, 2, 1, 0, 0),
            (2, 3, 2, 0, 0),
            (3, 2, 18, 0, 1),
            (3, 2, 19, 0, 1),
            (4, 2, 20, 0, 0),
            (5, 2, 5, 0, 0),
            (5, 2, 6, 0, 0),
            (6, 2, 3, 1, 1),
            (6, 2, 4, 1, 1),
            (7, 1, 21, 0, 0),
            (8, 2, 17, 1, 0),
            (9, 2, 22, 1, 0),
            (10, 2, 9, 0, 1),
            (10, 2, 10, 0, 1),
            (10, 1, 11, 0, 1),
            (11, 1, 12, 0, 0),
            (12, 1, 13, 0, 0),
            (13, 2, 14, 0, 0),
            (14, 2, 15, 0, 0),
        ),
    ),
    2: (
        2,
        0x1FF,
        (
            (0, 2, 23, 0, 0),
            (0, 2, 24, 0, 0),
            (1, 2, 18, 0, 0),
            (2, 2, 19, 0, 0),
            (3, 2, 5, 0, 0),
            (4, 2, 9, 0, 1),
            (4, 2, 10, 0, 1),
            (4, 1, 11, 0, 1),
            (5, 1, 12, 0, 0),
            (6, 1, 13, 0, 0),
            (7, 2, 14, 0, 0),
            (8, 2, 15, 0, 0),
        ),
    ),
    3: (
        2,
        0x3FF,
        (
            (0, 2, 23, 0, 0),
            (1, 2, 18, 0, 0),
            (2, 2, 19, 0, 0),
            (3, 2, 5, 0, 0),
            (4, 2, 20, 0, 0),
            (5, 2, 9, 0, 1),
            (5, 2, 10, 0, 1),
            (5, 1, 11, 0, 1),
            (6, 1, 12, 0, 0),
            (7, 1, 13, 0, 0),
            (8, 2, 14, 0, 0),
            (9, 2, 15, 0, 0),
        ),
    ),
    4: (
        2,
        0x1FFF,
        (
            (0, 1, 25, 0, 0),
            (0, 2, 26, 0, 0),
            (1, 1, 27, 0, 0),
            (2, 3, 2, 0, 0),
            (3, 2, 7, 0, 0),
            (4, 2, 8, 0, 0),
            (5, 2, 17, 1, 0),
            (6, 2, 22, 1, 0),
            (7, 1, 21, 0, 0),
            (8, 2, 9, 0, 1),
            (8, 2, 10, 0, 1),
            (8, 1, 11, 0, 1),
            (9, 1, 12, 0, 0),
            (10, 1, 13, 0, 0),
            (11, 2, 14, 0, 0),
            (12, 2, 15, 0, 0),
        ),
    ),
    5: (
        2,
        0x1FFF,
        (
            (0, 2, 0, 0, 0),
            (1, 2, 1, 0, 0),
            (2, 2, 28, 0, 0),
            (3, 2, 29, 0, 0),
            (4, 3, 2, 0, 0),
            (5, 1, 21, 0, 0),
            (6, 2, 17, 1, 0),
            (7, 2, 22, 1, 0),
            (8, 2, 9, 0, 1),
            (8, 2, 10, 0, 1),
            (8, 1, 11, 0, 1),
            (9, 1, 12, 0, 0),
            (10, 1, 13, 0, 0),
            (11, 2, 14, 0, 0),
            (12, 2, 15, 0, 0),
        ),
    ),
}


@dataclass(frozen=True, slots=True)
class MeasurementFormatOptions:
    resistance_format: str = "uint8Whole"
    treadmill_pace_format: str = "uint16"

    def __post_init__(self) -> None:
        if self.resistance_format not in (
            "uint8Whole",
            "signed16Tenths",
        ) or self.treadmill_pace_format not in ("uint16", "uint8Legacy"):
            raise RawCodecError("range", "invalid measurement format")


@dataclass(frozen=True, slots=True)
class MeasurementRaw:
    kind: int
    flags: int
    present: int
    unavailable: int
    values: tuple[int, ...]
    more_data: int = 0
    backward: int = 0
    truncated: int = 0
    trailing_bytes: int = 0
    reserved_flags: int = 0
    bytes_read: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not int
            or self.kind not in D
            or type(self.flags) is not int
            or not 0 <= self.flags <= 0xFFFFFF
            or type(self.values) is not tuple
            or len(self.values) != 30
            or any(type(x) is not int for x in self.values)
            or any(
                type(x) is not int or not 0 <= x < (1 << 30)
                for x in (self.present, self.unavailable)
            )
            or any(
                type(x) is not int or x not in (0, 1)
                for x in (
                    self.more_data,
                    self.backward,
                    self.truncated,
                    self.trailing_bytes,
                    self.reserved_flags,
                )
            )
            or type(self.bytes_read) is not int
            or self.bytes_read < 0
        ):
            raise RawCodecError("range", "invalid raw measurement")


def _fields(k: int, o: MeasurementFormatOptions) -> Iterator[tuple[int, int, int, int, int]]:
    for bit, w, i, s, u in D[k][2]:
        if o.resistance_format == "signed16Tenths" and i == 21 and k in (1, 4, 5):
            w, s = 2, 1
        if o.treadmill_pace_format == "uint8Legacy" and k == 0 and i in (7, 8):
            w = 1
        yield bit, w, i, s, u


def _sel(f: int, b: int) -> bool:
    return (f & 1) == 0 if b == 0 else bool(f & (1 << b))


def _options(options: MeasurementFormatOptions | None) -> MeasurementFormatOptions:
    if options is None:
        return MeasurementFormatOptions()
    if not isinstance(options, MeasurementFormatOptions):
        raise RawCodecError("kind", "options must be MeasurementFormatOptions")
    return options


def decode_measurement_raw(
    data: bytes | bytearray | memoryview, kind: int, options: MeasurementFormatOptions | None = None
) -> MeasurementRaw:
    if type(kind) is not int or kind not in D:
        raise RawCodecError("kind", "invalid measurement kind")
    b = immutable_bytes(data)
    o = _options(options)
    fb, valid, _ = D[kind]
    if len(b) < fb:
        raise RawCodecError("length", "truncated flags")
    f = int.from_bytes(b[:fb], "little")
    v = [0] * 30
    p = u = 0
    off = fb
    for bit, w, i, s, un in _fields(kind, o):
        if not _sel(f, bit):
            continue
        if off + w > len(b):
            return MeasurementRaw(
                kind,
                f,
                p,
                u,
                tuple(v),
                f & 1,
                int(kind == 1 and bool(f & 0x8000)),
                1,
                0,
                int(bool(f & ~valid)),
                off,
            )
        raw = int.from_bytes(b[off : off + w], "little")
        off += w
        p |= 1 << i
        sent = 0x7FFF if s else (0xFF if w == 1 else 0xFFFF)
        if un and raw == sent:
            u |= 1 << i
        else:
            v[i] = raw - (1 << (8 * w)) if s and raw & (1 << (8 * w - 1)) else raw
    return MeasurementRaw(
        kind,
        f,
        p,
        u,
        tuple(v),
        f & 1,
        int(kind == 1 and bool(f & 0x8000)),
        0,
        int(off < len(b)),
        int(bool(f & ~valid)),
        off,
    )


def encode_measurement_raw(
    m: MeasurementRaw, options: MeasurementFormatOptions | None = None
) -> bytes:
    o = _options(options)
    if not isinstance(m, MeasurementRaw):
        raise RawCodecError("kind", "value must be MeasurementRaw")
    fb, valid, _ = D[m.kind]
    if m.flags & ~valid or m.unavailable & ~m.present:
        raise RawCodecError("range", "RFU flags or invalid unavailable mask")
    need = 0
    out = bytearray(m.flags.to_bytes(fb, "little"))
    for bit, w, i, s, un in _fields(m.kind, o):
        if not _sel(m.flags, bit):
            continue
        need |= 1 << i
        v = m.values[i]
        if m.unavailable & (1 << i):
            if not un:
                raise RawCodecError("range", "field has no unavailable sentinel")
            v = 0x7FFF if s else (0xFF if w == 1 else 0xFFFF)
        else:
            lo = -(1 << (8 * w - 1)) if s else 0
            hi = (1 << (8 * w - 1)) - 1 if s else (1 << (8 * w)) - 1
            if not lo <= v <= hi or (un and v == (0x7FFF if s else (0xFF if w == 1 else 0xFFFF))):
                raise RawCodecError("range", "field outside wire range")
        out.extend(int(v).to_bytes(w, "little", signed=bool(s)))
    if m.present != need:
        raise RawCodecError("range", "present mask must exactly match flags")
    return bytes(out)


# Canonical codec-v1 normalized projection.  Raw evidence remains authoritative.
_METRICS = (
    "hrBpm",
    "powerWatts",
    "averagePowerWatts",
    "cadenceRpm",
    "averageCadenceRpm",
    "speedMps",
    "averageSpeedMps",
    "distanceMeters",
    "elapsedTimeSeconds",
    "remainingTimeSeconds",
    "energyKcal",
    "energyPerHourKcal",
    "energyPerMinuteKcal",
    "metabolicEquivalent",
    "stepCount",
    "stepRateSpm",
    "averageStepRateSpm",
    "strideCount",
    "floorCount",
    "positiveElevationGainMeters",
    "negativeElevationGainMeters",
    "inclinationPercent",
    "rampAngleDegrees",
    "resistanceLevel",
    "instantaneousPaceSecondsPer500m",
    "averagePaceSecondsPer500m",
    "forceOnBeltNewtons",
    "strokeRateSpm",
    "averageStrokeRateSpm",
    "strokeCount",
    "movementDirection",
)


def normalize_measurement(
    raw: MeasurementRaw, options: MeasurementFormatOptions | None = None
) -> dict[str, float | int | str | None]:
    """Project raw evidence into codec-v1 physical units; unavailable/unread values are ``None``."""
    o = _options(options)
    if not isinstance(raw, MeasurementRaw):
        raise RawCodecError("kind", "value must be MeasurementRaw")
    result: dict[str, float | int | str | None] = {k: None for k in _METRICS}

    def value(i: int, divisor: int = 1) -> float | int | None:
        if not raw.present & (1 << i) or raw.unavailable & (1 << i):
            return None
        return raw.values[i] / divisor if divisor != 1 else raw.values[i]

    for i, k, d in (
        (0, "speedMps", 360),
        (1, "averageSpeedMps", 360),
        (2, "distanceMeters", 1),
        (3, "inclinationPercent", 10),
        (4, "rampAngleDegrees", 10),
        (5, "positiveElevationGainMeters", 10 if raw.kind == 0 else 1),
        (6, "negativeElevationGainMeters", 10 if raw.kind == 0 else 1),
        (7, "instantaneousPaceSecondsPer500m", 1),
        (8, "averagePaceSecondsPer500m", 1),
        (9, "energyKcal", 1),
        (10, "energyPerHourKcal", 1),
        (11, "energyPerMinuteKcal", 1),
        (12, "hrBpm", 1),
        (13, "metabolicEquivalent", 10),
        (14, "elapsedTimeSeconds", 1),
        (15, "remainingTimeSeconds", 1),
        (16, "forceOnBeltNewtons", 1),
        (17, "powerWatts", 1),
        (18, "stepRateSpm", 1),
        (19, "averageStepRateSpm", 1),
        (20, "strideCount", 10 if raw.kind == 1 else 1),
        (
            21,
            "resistanceLevel",
            10 if o.resistance_format == "signed16Tenths" and raw.kind in (1, 4, 5) else 1,
        ),
        (22, "averagePowerWatts", 1),
        (23, "floorCount", 1),
        (24, "stepCount", 1),
        (25, "strokeRateSpm", 2),
        (26, "strokeCount", 1),
        (27, "averageStrokeRateSpm", 2),
        (28, "cadenceRpm", 2),
        (29, "averageCadenceRpm", 2),
    ):
        result[k] = value(i, d)
    if raw.kind == 0 and o.treadmill_pace_format == "uint8Legacy":
        result["instantaneousPaceSecondsPer500m"] = result["averagePaceSecondsPer500m"] = None
    if raw.kind == 1:
        result["movementDirection"] = "backward" if raw.backward else "forward"
    return result
