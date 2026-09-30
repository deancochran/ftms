"""Pure evaluation of caller-supplied FTMS discovery evidence.

This module deliberately performs no Bluetooth I/O and never says whether a
caller may execute a control procedure.  ``prerequisite`` is only a static
protocol-evidence result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ._errors import RawCodecError
from .ranges import RangeFormatOptions, RangeKind, decode_supported_range_raw


class DiscoveryState(IntEnum):
    NOT_ATTEMPTED = 0
    PARTIAL = 1
    COMPLETE = 2
    FAILED = 3


class ServiceScope(IntEnum):
    UNKNOWN = 0
    PRESENT = 1
    ABSENT = 2
    AMBIGUOUS = 3


class ReadState(IntEnum):
    NOT_ATTEMPTED = 0
    SUCCESS = 1
    FAILED = 2


class ReadReason(IntEnum):
    NONE = 0
    GENERIC = 1
    SECURITY_REQUIRED = 2
    UNAVAILABLE = 3
    TIMEOUT = 4
    DISCONNECTED = 5


class TruthValue(IntEnum):
    UNKNOWN = 0
    FALSE = 1
    TRUE = 2


class Presence(IntEnum):
    UNKNOWN = 0
    ABSENT = 1
    UNIQUE = 2
    AMBIGUOUS = 3


class DecodeState(IntEnum):
    NOT_ATTEMPTED = 0
    VALID = 1
    MALFORMED = 2
    FAILED = 3


class Declaration(IntEnum):
    UNKNOWN = 0
    NOT_SUPPORTED = 1
    SUPPORTED = 2


class Prerequisite(IntEnum):
    NOT_APPLICABLE = 0
    SATISFIED = 1
    INCOMPLETE = 2
    INCONSISTENT = 3


@dataclass(frozen=True, slots=True)
class C7Evidence:
    bonding_supported: TruthValue = TruthValue.UNKNOWN
    feature_may_change_over_lifetime: TruthValue = TruthValue.UNKNOWN

    def __post_init__(self) -> None:
        _enum(self.bonding_supported, TruthValue, "bonding_supported")
        _enum(self.feature_may_change_over_lifetime, TruthValue, "feature_may_change_over_lifetime")


@dataclass(frozen=True, slots=True)
class CharacteristicEvidence:
    uuid: str
    properties: int
    read_state: ReadState
    read_reason: ReadReason = ReadReason.NONE
    read_bytes: bytes = b""

    def __post_init__(self) -> None:
        if (
            type(self.uuid) is not str
            or len(self.uuid) != 32
            or any(c not in "0123456789abcdef" for c in self.uuid)
        ):
            raise ValueError("uuid must be 32 lowercase hexadecimal characters")
        if type(self.properties) is not int or not 0 <= self.properties <= 0xFFFF:
            raise ValueError("properties must be an unsigned 16-bit integer")
        _enum(self.read_state, ReadState, "read_state")
        _enum(self.read_reason, ReadReason, "read_reason")
        if self.read_state is not ReadState.FAILED and self.read_reason is not ReadReason.NONE:
            raise ValueError("read_reason is only valid for failed reads")
        if not isinstance(self.read_bytes, bytes):
            raise TypeError("read_bytes must be immutable bytes")
        if self.read_state is not ReadState.SUCCESS and self.read_bytes:
            raise ValueError("read_bytes are only valid for successful reads")


@dataclass(frozen=True, slots=True)
class CapabilitySnapshot:
    discovery: DiscoveryState
    scope: ServiceScope
    generation: int
    characteristics: tuple[CharacteristicEvidence, ...]
    c7: C7Evidence | None = None

    def __post_init__(self) -> None:
        _enum(self.discovery, DiscoveryState, "discovery")
        _enum(self.scope, ServiceScope, "scope")
        if type(self.generation) is not int or not 0 <= self.generation <= 0xFFFFFFFF:
            raise ValueError("generation must be an unsigned 32-bit integer")
        if not isinstance(self.characteristics, tuple) or not all(
            isinstance(x, CharacteristicEvidence) for x in self.characteristics
        ):
            raise TypeError("characteristics must be a tuple of CharacteristicEvidence")
        if self.c7 is not None and not isinstance(self.c7, C7Evidence):
            raise TypeError("c7 must be C7Evidence or None")


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Immutable static report; it intentionally has no execution-authority field."""

    generation: int
    discovery: DiscoveryState
    scope: ServiceScope
    observation_count: int
    presence: tuple[Presence, ...]
    feature: tuple[int | None, ...]
    ranges: tuple[tuple[object, ...], ...]
    operations: tuple[tuple[int, ...], ...]
    observations: tuple[tuple[object, ...], ...]
    diagnostics: tuple[tuple[int | None, ...], ...]

    def __post_init__(self) -> None:
        _enum(self.discovery, DiscoveryState, "discovery")
        _enum(self.scope, ServiceScope, "scope")
        if type(self.generation) is not int or not 0 <= self.generation <= 0xFFFFFFFF:
            raise ValueError("generation must be an unsigned 32-bit integer")
        if type(self.observation_count) is not int or self.observation_count < 0:
            raise ValueError("observation_count must be a nonnegative integer")
        for rows in (
            self.presence,
            self.feature,
            self.ranges,
            self.operations,
            self.observations,
            self.diagnostics,
        ):
            if type(rows) is not tuple:
                raise TypeError("report collections must be immutable tuples")
            _immutable_report_value(rows)

    def to_wire(self) -> dict[str, object]:
        """Return the immutable corpus-normalized report as fresh caller-owned containers."""
        return {
            "generation": self.generation,
            "discovery": int(self.discovery),
            "scope": int(self.scope),
            "observationCount": self.observation_count,
            "diagnosticCount": len(self.diagnostics),
            "presence": [int(x) for x in self.presence],
            "feature": list(self.feature),
            "ranges": [
                [*x[:3], list(x[3]) if isinstance(x[3], tuple) else None] for x in self.ranges
            ],
            "operations": [list(x) for x in self.operations],
            "observations": [list(x) for x in self.observations],
            "diagnostics": [list(x) for x in self.diagnostics],
        }


_READ, _WRITE, _NOTIFY, _INDICATE = 2, 8, 16, 32
_BASE = "0000{}00001000800000805f9b34fb"
_TARGETS = (255, 255, 0, 1, 2, 3, 4, 255, 255, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
_RANGE_FOR_TARGET = (0, 1, 2, 4, 3)


def _immutable_report_value(value: object) -> None:
    if type(value) is tuple:
        for item in value:
            _immutable_report_value(item)
    elif value is not None and type(value) not in (int, str) and not isinstance(value, IntEnum):
        raise TypeError("report rows must contain only immutable tuples, integers, strings or None")


def _enum(value: object, cls: type[IntEnum], name: str) -> None:
    if not isinstance(value, cls):
        raise TypeError(f"{name} must be {cls.__name__}")


def _kind(uuid: str) -> int:
    if not uuid.startswith("0000") or not uuid.endswith("00001000800000805f9b34fb"):
        return 0
    value = int(uuid[4:8], 16)
    return value - 0x2ACC + 1 if 0x2ACC <= value <= 0x2ADA else 0


def _c7_unknown(c7: C7Evidence | None) -> bool:
    return c7 is None or (
        c7.bonding_supported is not TruthValue.FALSE
        and c7.feature_may_change_over_lifetime is not TruthValue.FALSE
        and not (
            c7.bonding_supported is TruthValue.TRUE
            and c7.feature_may_change_over_lifetime is TruthValue.TRUE
        )
    )


def _required(kind: int, c7: C7Evidence | None) -> int:
    if kind == 1:
        return _READ | (
            _INDICATE
            if c7 is not None
            and c7.bonding_supported is TruthValue.TRUE
            and c7.feature_may_change_over_lifetime is TruthValue.TRUE
            else 0
        )
    if kind == 8:
        return _READ | _NOTIFY
    if kind == 14:
        return _WRITE | _INDICATE
    if 9 <= kind <= 13:
        return _READ
    return _NOTIFY


def _decode_feature(c: CharacteristicEvidence) -> tuple[DecodeState, int, int]:
    if c.read_state is ReadState.FAILED:
        return DecodeState.FAILED, 0, 0
    if c.read_state is not ReadState.SUCCESS:
        return DecodeState.NOT_ATTEMPTED, 0, 0
    if len(c.read_bytes) != 8:
        return DecodeState.MALFORMED, 0, 0
    return (
        DecodeState.VALID,
        int.from_bytes(c.read_bytes[:4], "little"),
        int.from_bytes(c.read_bytes[4:], "little"),
    )


def _decode_range(
    c: CharacteristicEvidence, kind: int, options: RangeFormatOptions | None
) -> tuple[DecodeState, tuple[int, ...] | None]:
    if c.read_state is ReadState.FAILED:
        return DecodeState.FAILED, None
    if c.read_state is not ReadState.SUCCESS:
        return DecodeState.NOT_ATTEMPTED, None
    # Capability corpus range order: speed, inclination, resistance, heart rate, power.
    mapped = kind - 9
    names: tuple[RangeKind, ...] = ("speed", "inclination", "resistance", "heartRate", "power")
    try:
        raw = decode_supported_range_raw(
            c.read_bytes, names[mapped], options if kind == 11 else None
        )
    except RawCodecError:
        return DecodeState.MALFORMED, None
    return DecodeState.VALID, (
        mapped,
        raw.minimum,
        raw.maximum,
        raw.increment,
        raw.scale_divisor,
        mapped,
    )


def evaluate_capabilities(
    snapshot: CapabilitySnapshot, options: RangeFormatOptions | None = None
) -> CapabilityReport:
    """Evaluate one caller-owned service snapshot without I/O or control authority."""
    if not isinstance(snapshot, CapabilitySnapshot):
        raise TypeError("snapshot must be CapabilitySnapshot")
    if options is not None:
        if not isinstance(options, RangeFormatOptions):
            raise TypeError("options must be RangeFormatOptions or None")
        if options.resistance_format not in ("uint8Whole", "signed16Tenths"):
            raise ValueError("unsupported resistance range format")
    cs = snapshot.characteristics
    kinds = tuple(_kind(c.uuid) for c in cs)
    first = [-1] * 16
    counts = [0] * 16
    for index, kind in enumerate(kinds):
        if kind:
            if first[kind] < 0:
                first[kind] = index
            counts[kind] = min(2, counts[kind] + 1)
    scope_ok = snapshot.scope is ServiceScope.PRESENT
    presence = [Presence.UNKNOWN] * 16
    diagnostics: list[tuple[int, int, int | None]] = []
    for kind in range(1, 16):
        if counts[kind] == 2:
            presence[kind] = Presence.AMBIGUOUS
            diagnostics.append((3, kind, first[kind]))
        elif counts[kind] == 1:
            presence[kind] = Presence.UNIQUE
        elif scope_ok and snapshot.discovery is DiscoveryState.COMPLETE:
            presence[kind] = Presence.ABSENT
    absent = (
        snapshot.scope is ServiceScope.ABSENT
        and snapshot.discovery is DiscoveryState.COMPLETE
        and not cs
    )
    if not scope_ok:
        diagnostics.append((0, 0, None))
    if snapshot.scope is ServiceScope.ABSENT and not absent:
        diagnostics.append((11, 0, None))
    if snapshot.discovery is not DiscoveryState.COMPLETE:
        diagnostics.append((2 if snapshot.discovery is DiscoveryState.FAILED else 1, 0, None))
    for index, (c, kind) in enumerate(zip(cs, kinds, strict=True)):
        if not kind or not scope_ok:
            continue
        expected = _required(kind, snapshot.c7)
        unknown_c7 = kind == 1 and _c7_unknown(snapshot.c7)
        if c.properties & expected != expected:
            diagnostics.append((5, kind, index))
        permitted = expected | (_INDICATE if unknown_c7 else 0)
        if c.properties & ~permitted:
            diagnostics.append((6, kind, index))
        if unknown_c7:
            diagnostics.append((12, kind, index))
        if c.read_state is ReadState.FAILED:
            diagnostics.append(
                (8 if c.read_reason is ReadReason.SECURITY_REQUIRED else 7, kind, index)
            )
    feature_index = first[1] if scope_ok and presence[1] is Presence.UNIQUE else -1
    fstate, machine, target = (
        _decode_feature(cs[feature_index])
        if feature_index >= 0
        else (DecodeState.NOT_ATTEMPTED, 0, 0)
    )
    feature = (
        int(presence[1]),
        int(fstate),
        feature_index if feature_index >= 0 else None,
        machine,
        target,
        machine & 0xFFFE0000,
        target & 0xFFFE0000,
    )
    if fstate is DecodeState.MALFORMED:
        diagnostics.append((9, 1, feature_index))
    ranges: list[tuple[object, ...]] = []
    rstates: list[DecodeState] = []
    for offset in range(5):
        kind = 9 + offset
        index = first[kind] if scope_ok and presence[kind] is Presence.UNIQUE else -1
        state, value = (
            _decode_range(cs[index], kind, options)
            if index >= 0
            else (DecodeState.NOT_ATTEMPTED, None)
        )
        rstates.append(state)
        ranges.append((int(presence[kind]), int(state), index if index >= 0 else None, value))
        if state is DecodeState.MALFORMED:
            diagnostics.append((9, kind, index))
    if scope_ok:
        if presence[1] is Presence.ABSENT:
            diagnostics.append((4, 1, None))
        if (
            presence[14] in (Presence.UNIQUE, Presence.AMBIGUOUS)
            and presence[15] is Presence.ABSENT
        ):
            diagnostics.append((4, 15, None))
        if fstate is DecodeState.VALID:
            if target & 0x1FFFF and presence[14] is Presence.ABSENT:
                diagnostics.append((4, 14, None))
            for bit in range(5):
                range_kind = 9 + _RANGE_FOR_TARGET[bit]
                if target & (1 << bit) and presence[range_kind] is Presence.ABSENT:
                    diagnostics.append((10, range_kind, None))

    def char_reasons(kind: int, unavailable: int, invalid: int) -> int:
        if presence[kind] is Presence.UNKNOWN:
            return unavailable
        if presence[kind] is not Presence.UNIQUE:
            return invalid
        props = cs[first[kind]].properties
        if kind == 1 and _c7_unknown(snapshot.c7):
            return 1024 | (invalid if not (props & _READ) or props & ~(_READ | _INDICATE) else 0)
        return 0 if props == _required(kind, snapshot.c7) else invalid

    operations: list[tuple[int, ...]] = []
    for opcode, bit in enumerate(_TARGETS):
        declaration = Declaration.UNKNOWN
        reasons = 0
        if not scope_ok:
            if absent:
                declaration, prerequisite = Declaration.NOT_SUPPORTED, Prerequisite.NOT_APPLICABLE
            else:
                prerequisite = (
                    Prerequisite.INCONSISTENT
                    if snapshot.scope is ServiceScope.ABSENT
                    else Prerequisite.INCOMPLETE
                )
            operations.append(
                (opcode, bit, int(opcode in (18, 19)), int(declaration), int(prerequisite), 1)
            )
            continue
        if bit == 255:
            declaration = (
                Declaration.SUPPORTED
                if presence[14] is Presence.UNIQUE
                else Declaration.NOT_SUPPORTED
                if presence[14] is Presence.ABSENT
                else Declaration.UNKNOWN
            )
        elif fstate is DecodeState.VALID:
            declaration = (
                Declaration.SUPPORTED if target & (1 << bit) else Declaration.NOT_SUPPORTED
            )
        if declaration is Declaration.NOT_SUPPORTED:
            operations.append((opcode, bit, int(opcode in (18, 19)), int(declaration), 0, 0))
            continue
        if snapshot.discovery is not DiscoveryState.COMPLETE:
            reasons |= 2
        reasons |= char_reasons(1, 4, 8)
        if bit != 255 and presence[1] is Presence.UNIQUE:
            reasons |= (
                0 if fstate is DecodeState.VALID else 8 if fstate is DecodeState.MALFORMED else 4
            )
        reasons |= char_reasons(14, 16, 32) | char_reasons(15, 64, 128)
        if 0 <= bit <= 4 and declaration is Declaration.SUPPORTED:
            ri = _RANGE_FOR_TARGET[bit]
            rk = 9 + ri
            reasons |= char_reasons(rk, 256, 512)
            if presence[rk] is Presence.UNIQUE:
                reasons |= (
                    0
                    if rstates[ri] is DecodeState.VALID
                    else 512
                    if rstates[ri] is DecodeState.MALFORMED
                    else 256
                )
        prerequisite = (
            Prerequisite.INCONSISTENT
            if reasons & (8 | 32 | 128 | 512)
            else Prerequisite.SATISFIED
            if not reasons
            else Prerequisite.INCOMPLETE
        )
        operations.append(
            (opcode, bit, int(opcode in (18, 19)), int(declaration), int(prerequisite), reasons)
        )
    observations = tuple(
        (i, c.uuid, c.properties, kind, int(c.read_state), int(c.read_reason), len(c.read_bytes))
        for i, (c, kind) in enumerate(zip(cs, kinds, strict=True))
    )
    return CapabilityReport(
        snapshot.generation,
        snapshot.discovery,
        snapshot.scope,
        len(cs),
        tuple(presence),
        feature,
        tuple(ranges),
        tuple(operations),
        observations,
        tuple(diagnostics),
    )
