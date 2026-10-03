"""Raw, transport-independent FTMS measurement codecs."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

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


@dataclass(frozen=True, slots=True)
class NormalizedMeasurement:
    """Named physical values projected from one explicitly formatted raw packet."""

    hr_bpm: float | int | None = None
    power_watts: float | int | None = None
    average_power_watts: float | int | None = None
    cadence_rpm: float | int | None = None
    average_cadence_rpm: float | int | None = None
    speed_mps: float | int | None = None
    average_speed_mps: float | int | None = None
    distance_meters: float | int | None = None
    elapsed_time_seconds: float | int | None = None
    remaining_time_seconds: float | int | None = None
    energy_kcal: float | int | None = None
    energy_per_hour_kcal: float | int | None = None
    energy_per_minute_kcal: float | int | None = None
    metabolic_equivalent: float | int | None = None
    step_count: float | int | None = None
    step_rate_spm: float | int | None = None
    average_step_rate_spm: float | int | None = None
    stride_count: float | int | None = None
    floor_count: float | int | None = None
    positive_elevation_gain_meters: float | int | None = None
    negative_elevation_gain_meters: float | int | None = None
    inclination_percent: float | int | None = None
    ramp_angle_degrees: float | int | None = None
    resistance_level: float | int | None = None
    instantaneous_pace_seconds_per_500m: float | int | None = None
    average_pace_seconds_per_500m: float | int | None = None
    force_on_belt_newtons: float | int | None = None
    stroke_rate_spm: float | int | None = None
    average_stroke_rate_spm: float | int | None = None
    stroke_count: float | int | None = None
    movement_direction: str | None = None


@dataclass(frozen=True, slots=True)
class MeasurementDiagnostics:
    """Typed decode evidence; raw masks and values remain available on ``raw``."""

    more_data: bool
    backward: bool
    truncated: bool
    trailing_bytes: bool
    reserved_flags: bool
    bytes_read: int


@dataclass(frozen=True, slots=True)
class DecodedMeasurement:
    """Raw evidence, selected wire format, diagnostics, and named physical values."""

    raw: MeasurementRaw
    format: MeasurementFormatOptions
    metrics: NormalizedMeasurement

    @property
    def diagnostics(self) -> MeasurementDiagnostics:
        return MeasurementDiagnostics(
            bool(self.raw.more_data),
            bool(self.raw.backward),
            bool(self.raw.truncated),
            bool(self.raw.trailing_bytes),
            bool(self.raw.reserved_flags),
            self.raw.bytes_read,
        )


@dataclass(frozen=True, slots=True)
class MeasurementDecodeResult:
    """UUID-dispatched measurement result; unsupported UUIDs are never layout-inferred."""

    measurement: DecodedMeasurement | None
    unsupported_uuid: str | None = None

    @property
    def known(self) -> bool:
        return self.measurement is not None


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


def _normalize_values(
    raw: MeasurementRaw, options: MeasurementFormatOptions | None = None
) -> dict[str, float | int | str | None]:
    """Single canonical raw-to-physical projection used by both public views."""
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


def normalize_measurement(
    raw: MeasurementRaw, options: MeasurementFormatOptions | None = None
) -> dict[str, float | int | str | None]:
    """Project raw evidence into codec-v1 physical units; unavailable/unread values are ``None``."""
    return _normalize_values(raw, options)


_TYPED_METRIC_NAMES = {
    "hrBpm": "hr_bpm",
    "powerWatts": "power_watts",
    "averagePowerWatts": "average_power_watts",
    "cadenceRpm": "cadence_rpm",
    "averageCadenceRpm": "average_cadence_rpm",
    "speedMps": "speed_mps",
    "averageSpeedMps": "average_speed_mps",
    "distanceMeters": "distance_meters",
    "elapsedTimeSeconds": "elapsed_time_seconds",
    "remainingTimeSeconds": "remaining_time_seconds",
    "energyKcal": "energy_kcal",
    "energyPerHourKcal": "energy_per_hour_kcal",
    "energyPerMinuteKcal": "energy_per_minute_kcal",
    "metabolicEquivalent": "metabolic_equivalent",
    "stepCount": "step_count",
    "stepRateSpm": "step_rate_spm",
    "averageStepRateSpm": "average_step_rate_spm",
    "strideCount": "stride_count",
    "floorCount": "floor_count",
    "positiveElevationGainMeters": "positive_elevation_gain_meters",
    "negativeElevationGainMeters": "negative_elevation_gain_meters",
    "inclinationPercent": "inclination_percent",
    "rampAngleDegrees": "ramp_angle_degrees",
    "resistanceLevel": "resistance_level",
    "instantaneousPaceSecondsPer500m": "instantaneous_pace_seconds_per_500m",
    "averagePaceSecondsPer500m": "average_pace_seconds_per_500m",
    "forceOnBeltNewtons": "force_on_belt_newtons",
    "strokeRateSpm": "stroke_rate_spm",
    "averageStrokeRateSpm": "average_stroke_rate_spm",
    "strokeCount": "stroke_count",
    "movementDirection": "movement_direction",
}
_MEASUREMENT_UUIDS = {
    "00002acd00001000800000805f9b34fb": 0,
    "00002ace00001000800000805f9b34fb": 1,
    "00002acf00001000800000805f9b34fb": 2,
    "00002ad000001000800000805f9b34fb": 3,
    "00002ad100001000800000805f9b34fb": 4,
    "00002ad200001000800000805f9b34fb": 5,
}


def decode_measurement(
    characteristic_uuid: str,
    data: bytes | bytearray | memoryview,
    format: MeasurementFormatOptions | None = None,
) -> MeasurementDecodeResult:
    """Decode a full canonical Bluetooth UUID with an explicit measurement format.

    Full 32-hex and standard hyphenated UUIDs are case-insensitive. The simple
    4-hex and ``0x`` aliases are accepted too. Vendor and non-measurement UUIDs
    remain explicit unsupported results; this function never chooses a layout
    from bytes.
    """
    kind = _measurement_kind(characteristic_uuid)
    if kind is None:
        return MeasurementDecodeResult(
            None, characteristic_uuid if type(characteristic_uuid) is str else None
        )
    selected = _options(format)
    raw = decode_measurement_raw(data, kind, selected)
    normalized = _normalize_values(raw, selected)
    metrics = NormalizedMeasurement(
        **cast(Any, {typed: normalized[wire] for wire, typed in _TYPED_METRIC_NAMES.items()})
    )
    return MeasurementDecodeResult(DecodedMeasurement(raw, selected, metrics))


def _measurement_kind(uuid: object) -> int | None:
    """Accept only documented UUID spellings; never repair arbitrary punctuation."""
    if type(uuid) is not str:
        return None
    text = uuid
    if len(text) == 4 and all(c in "0123456789abcdefABCDEF" for c in text):
        return _MEASUREMENT_UUIDS.get(f"0000{text.lower()}00001000800000805f9b34fb")
    if (
        len(text) == 6
        and text[:2] in ("0x", "0X")
        and all(c in "0123456789abcdefABCDEF" for c in text[2:])
    ):
        return _MEASUREMENT_UUIDS.get(f"0000{text[2:].lower()}00001000800000805f9b34fb")
    if len(text) == 32 and all(c in "0123456789abcdefABCDEF" for c in text):
        return _MEASUREMENT_UUIDS.get(text.lower())
    if (
        len(text) == 36
        and all(text[index] == "-" for index in (8, 13, 18, 23))
        and all(
            c in "0123456789abcdefABCDEF"
            for index, c in enumerate(text)
            if index not in (8, 13, 18, 23)
        )
    ):
        return _MEASUREMENT_UUIDS.get(text.replace("-", "").lower())
    return None
