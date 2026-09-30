"""Raw Fitness Machine Status and Training Status codecs."""

from __future__ import annotations

from dataclasses import dataclass

from ._binary import immutable_bytes
from ._errors import RawCodecError

# Complete on-wire lengths, including the opcode byte.
_MACHINE_LENGTHS = {
    1: 1,
    2: 2,
    3: 1,
    4: 1,
    5: 3,
    6: 3,
    7: 3,
    8: 3,
    9: 2,
    10: 3,
    11: 3,
    12: 3,
    13: 4,
    14: 3,
    15: 5,
    16: 7,
    17: 11,
    18: 7,
    19: 3,
    20: 2,
    21: 3,
    255: 1,
}

_MACHINE_LABELS = {
    1: "reset",
    2: "stopped_or_paused_by_user",
    3: "stopped_by_safety_key",
    4: "started_or_resumed_by_user",
    5: "target_speed_changed",
    6: "target_inclination_changed",
    7: "target_resistance_changed",
    8: "target_power_changed",
    9: "target_heart_rate_changed",
    10: "targeted_expended_energy_changed",
    11: "targeted_steps_changed",
    12: "targeted_strides_changed",
    13: "targeted_distance_changed",
    14: "targeted_training_time_changed",
    15: "targeted_time_two_hr_zones_changed",
    16: "targeted_time_three_hr_zones_changed",
    17: "targeted_time_five_hr_zones_changed",
    18: "indoor_bike_simulation_parameters_changed",
    19: "wheel_circumference_changed",
    20: "spin_down_status",
    21: "targeted_cadence_changed",
    255: "control_permission_lost",
}

_TRAINING_LABELS = (
    "other",
    "idle",
    "warming_up",
    "low_intensity_interval",
    "high_intensity_interval",
    "recovery_interval",
    "isometric",
    "heart_rate_control",
    "fitness_test",
    "speed_outside_control_region_low",
    "speed_outside_control_region_high",
    "cool_down",
    "watt_control",
    "manual_mode",
    "pre_workout",
    "post_workout",
)


def _bit(value: object) -> bool:
    return type(value) is int and value in (0, 1)


@dataclass(frozen=True, slots=True)
class MachineStatusRaw:
    opcode: int
    action: int = 0
    parameter: tuple[int, tuple[int, ...]] | None = None
    unknown_opcode: int = 0
    reserved_value: int = 0
    truncated: int = 0
    trailing_bytes: int = 0

    def __post_init__(self) -> None:
        parameter_ok = self.parameter is None or (
            type(self.parameter) is tuple
            and len(self.parameter) == 2
            and type(self.parameter[0]) is int
            and 0 <= self.parameter[0] <= 255
            and type(self.parameter[1]) is tuple
            and all(type(value) is int for value in self.parameter[1])
        )
        if (
            type(self.opcode) is not int
            or not 0 <= self.opcode <= 255
            or type(self.action) is not int
            or not 0 <= self.action <= 255
            or not parameter_ok
            or not all(
                _bit(value)
                for value in (
                    self.unknown_opcode,
                    self.reserved_value,
                    self.truncated,
                    self.trailing_bytes,
                )
            )
        ):
            raise RawCodecError("range", "invalid machine status")


@dataclass(frozen=True, slots=True)
class TrainingStatusRaw:
    flags: int
    code: int
    text: bytes = b""
    text_offset: int = 0
    text_size: int = 0
    text_present: int = 0
    extended_string: int = 0
    reserved_flags: int = 0
    reserved_value: int = 0
    invalid_flags: int = 0
    invalid_utf8: int = 0
    truncated: int = 0
    trailing_bytes: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.flags) is not int
            or not 0 <= self.flags <= 255
            or type(self.code) is not int
            or not 0 <= self.code <= 255
            or type(self.text) is not bytes
            or type(self.text_offset) is not int
            or self.text_offset < 0
            or type(self.text_size) is not int
            or self.text_size < 0
            or type(self.reserved_flags) is not int
            or not 0 <= self.reserved_flags <= 255
            or not all(
                _bit(value)
                for value in (
                    self.text_present,
                    self.extended_string,
                    self.reserved_value,
                    self.invalid_flags,
                    self.invalid_utf8,
                    self.truncated,
                    self.trailing_bytes,
                )
            )
        ):
            raise RawCodecError("range", "invalid training status")


def _operands(opcode: int, data: bytes) -> tuple[int, ...]:
    if opcode in (6, 7, 8):
        return (int.from_bytes(data, "little", signed=True),)
    if opcode == 18:
        return (
            int.from_bytes(data[:2], "little", signed=True),
            int.from_bytes(data[2:4], "little", signed=True),
            data[4],
            data[5],
        )
    if opcode in (15, 16, 17):
        return tuple(int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2))
    return (int.from_bytes(data, "little"),)


def _parameter_opcode(opcode: int) -> int | None:
    if 5 <= opcode <= 9:
        return opcode - 3
    if 10 <= opcode <= 19 or opcode == 21:
        return opcode - 1
    return None


def _decode_utf8_replacement(payload: bytes) -> str:
    """Match the TypeScript parser's deliberate, byte-by-byte UTF-8 replacement behavior."""
    result: list[str] = []
    index = 0
    while index < len(payload):
        first = payload[index]
        if first <= 0x7F:
            code_point, continuation_count = first, 0
        elif 0xC2 <= first <= 0xDF:
            code_point, continuation_count = first & 0x1F, 1
        elif 0xE0 <= first <= 0xEF:
            code_point, continuation_count = first & 0x0F, 2
        elif 0xF0 <= first <= 0xF4:
            code_point, continuation_count = first & 0x07, 3
        else:
            result.append("\ufffd")
            index += 1
            continue
        if index + continuation_count >= len(payload):
            result.append("\ufffd")
            break
        second = payload[index + 1] if continuation_count else 0
        valid = not (
            (first == 0xE0 and second < 0xA0)
            or (first == 0xED and second > 0x9F)
            or (first == 0xF0 and second < 0x90)
            or (first == 0xF4 and second > 0x8F)
        )
        for continuation_index in range(1, continuation_count + 1):
            continuation = payload[index + continuation_index]
            if continuation & 0xC0 != 0x80:
                valid = False
                break
            code_point = (code_point << 6) | (continuation & 0x3F)
        if not valid or code_point > 0x10FFFF or 0xD800 <= code_point <= 0xDFFF:
            result.append("\ufffd")
            index += 1
            continue
        result.append(chr(code_point))
        index += continuation_count + 1
    return "".join(result)


def decode_machine_status_raw(data: object) -> MachineStatusRaw:
    """Decode machine-status bytes while retaining unknown and malformed diagnostics."""
    payload = immutable_bytes(data)
    if not payload:
        return MachineStatusRaw(0, unknown_opcode=1, truncated=1)
    opcode = payload[0]
    length = _MACHINE_LENGTHS.get(opcode)
    if length is None:
        return MachineStatusRaw(opcode, unknown_opcode=1)
    if len(payload) < length:
        return MachineStatusRaw(opcode, truncated=1)
    action = payload[1] if opcode in (2, 20) else 0
    reserved = int(
        (opcode == 2 and action not in (1, 2)) or (opcode == 20 and action not in (1, 2, 3, 4))
    )
    parameter_opcode = _parameter_opcode(opcode)
    parameter = (
        None
        if parameter_opcode is None
        else (parameter_opcode, _operands(opcode, payload[1:length]))
    )
    return MachineStatusRaw(
        opcode,
        action,
        parameter,
        reserved_value=reserved,
        trailing_bytes=int(len(payload) > length),
    )


def _wire_int(value: object, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise RawCodecError("range", "operand outside wire range")
    return value


def encode_machine_status_raw(status: MachineStatusRaw) -> bytes:
    """Encode only canonical, fully specified machine-status raw values."""
    if not isinstance(status, MachineStatusRaw):
        raise RawCodecError("kind", "status must be MachineStatusRaw")
    opcode = status.opcode
    length = _MACHINE_LENGTHS.get(opcode)
    if length is None or any(
        (status.unknown_opcode, status.reserved_value, status.truncated, status.trailing_bytes)
    ):
        raise RawCodecError("range", "noncanonical machine status")
    if opcode in (2, 20):
        if status.parameter is not None:
            raise RawCodecError("range", "unexpected parameter")
        upper = 2 if opcode == 2 else 4
        return bytes((opcode, _wire_int(status.action, 1, upper)))
    if _parameter_opcode(opcode) is None:
        if status.action != 0 or status.parameter is not None:
            raise RawCodecError("range", "unexpected action or parameter")
        return bytes((opcode,))
    expected_opcode = _parameter_opcode(opcode)
    assert expected_opcode is not None
    if status.action != 0 or status.parameter is None or status.parameter[0] != expected_opcode:
        raise RawCodecError("kind", "wrong parameter")
    operands = status.parameter[1]
    count = 4 if opcode == 18 else 1 if opcode in (9, 13) else (length - 1) // 2
    if len(operands) != count:
        raise RawCodecError("length", "wrong parameter arity")
    if opcode == 18:
        ranges = ((-32768, 32767), (-32768, 32767), (0, 255), (0, 255))
        values = tuple(_wire_int(value, *ranges[index]) for index, value in enumerate(operands))
        return (
            bytes((opcode,))
            + values[0].to_bytes(2, "little", signed=True)
            + values[1].to_bytes(2, "little", signed=True)
            + bytes(values[2:])
        )
    signed = opcode in (6, 7, 8)
    width = 3 if opcode == 13 else 1 if opcode == 9 else 2
    low, high = (-32768, 32767) if signed else (0, (1 << (8 * width)) - 1)
    values = tuple(_wire_int(value, low, high) for value in operands)
    return bytes((opcode,)) + b"".join(
        value.to_bytes(width, "little", signed=signed) for value in values
    )


def decode_training_status_raw(data: object) -> TrainingStatusRaw:
    """Decode training-status bytes while preserving raw text and diagnostics."""
    payload = immutable_bytes(data)
    if len(payload) < 2:
        return TrainingStatusRaw(payload[0] if payload else 0, 0, truncated=1)
    flags, code = payload[:2]
    present = flags & 1
    text = payload[2:] if present else b""
    try:
        text.decode("utf-8")
        invalid_utf8 = 0
    except UnicodeDecodeError:
        invalid_utf8 = 1
    return TrainingStatusRaw(
        flags,
        code,
        text,
        2 if present else 0,
        len(text),
        present,
        (flags >> 1) & 1,
        flags & 0xFC,
        int(code > 15),
        int(bool((flags & 2) and not present)),
        invalid_utf8,
        0,
        int(not present and len(payload) > 2),
    )


def encode_training_status_raw(status: TrainingStatusRaw) -> bytes:
    """Encode flags/code/text; decoded offsets and string metadata are not encoder inputs."""
    if not isinstance(status, TrainingStatusRaw):
        raise RawCodecError("kind", "status must be TrainingStatusRaw")
    flags, code = status.flags, status.code
    present = flags & 1
    if (
        flags & 0xFC
        or (flags & 2 and not present)
        or code > 15
        or any(
            (
                status.reserved_flags,
                status.reserved_value,
                status.invalid_flags,
                status.invalid_utf8,
                status.truncated,
                status.trailing_bytes,
            )
        )
        or (not present and status.text)
    ):
        raise RawCodecError("range", "noncanonical training status")
    try:
        status.text.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RawCodecError("range", "invalid UTF-8") from error
    return bytes((flags, code)) + (status.text if present else b"")


def normalize_training_status(raw: TrainingStatusRaw) -> dict[str, object]:
    """Project raw training status to the TypeScript-compatible public status shape."""
    if not isinstance(raw, TrainingStatusRaw):
        raise RawCodecError("kind", "status must be TrainingStatusRaw")
    details: dict[str, object] | None = None
    if not raw.truncated:
        details = {
            "kind": "training_status",
            "flags": raw.flags,
            "stringPresent": bool(raw.text_present),
            "extendedStringPresent": bool(raw.extended_string),
        }
        if raw.text_present:
            details["trainingStatusString"] = _decode_utf8_replacement(raw.text)
    return {
        "code": raw.code if not raw.truncated else None,
        "label": _TRAINING_LABELS[raw.code]
        if not raw.truncated and raw.code < 16
        else ("unknown" if raw.truncated else "reserved"),
        "details": details,
    }


def normalize_machine_status(raw: MachineStatusRaw) -> dict[str, object]:
    """Project raw machine status to the TypeScript-compatible public status shape."""
    if not isinstance(raw, MachineStatusRaw):
        raise RawCodecError("kind", "status must be MachineStatusRaw")
    details: dict[str, object] | None = None
    operands = raw.parameter[1] if raw.parameter is not None else ()
    if not raw.truncated and not raw.unknown_opcode:
        if _parameter_opcode(raw.opcode) is not None:
            # Validate caller-constructed operands too, while retaining decoded
            # trailing/diagnostic evidence in the original result.
            encode_machine_status_raw(MachineStatusRaw(raw.opcode, raw.action, raw.parameter))
        if raw.opcode in (1, 3, 4, 255):
            details = {"kind": "none"}
        elif raw.opcode == 2:
            details = {
                "kind": "stop_pause",
                "action": {1: "stop", 2: "pause"}.get(raw.action, "reserved"),
            }
        elif raw.opcode == 5:
            details = {"kind": "speed", "speedKph": operands[0] / 100}
        elif raw.opcode == 6:
            details = {"kind": "inclination", "inclinationPercent": operands[0] / 10}
        elif raw.opcode == 7:
            details = {"kind": "resistance", "resistanceLevel": operands[0] / 10}
        elif raw.opcode == 8:
            details = {"kind": "power", "powerWatts": operands[0]}
        elif raw.opcode == 9:
            details = {"kind": "heart_rate", "heartRateBpm": operands[0]}
        elif raw.opcode in (10, 11, 12):
            key = {
                10: ("energy", "energyKcal"),
                11: ("steps", "steps"),
                12: ("strides", "strides"),
            }[raw.opcode]
            details = {"kind": key[0], key[1]: operands[0]}
        elif raw.opcode == 13:
            details = {"kind": "distance", "distanceMeters": operands[0]}
        elif raw.opcode == 14:
            details = {"kind": "training_time", "seconds": operands[0]}
        elif raw.opcode in (15, 16, 17):
            details = {"kind": "hr_zones", "seconds": list(operands)}
        elif raw.opcode == 18:
            details = {
                "kind": "simulation",
                "windSpeedMps": operands[0] / 1000,
                "gradePercent": operands[1] / 100,
                "crr": operands[2] / 10000,
                "cwKgPerM": operands[3] / 100,
            }
        elif raw.opcode == 19:
            details = {"kind": "wheel_circumference", "circumferenceMm": operands[0] / 10}
        elif raw.opcode == 20:
            details = {
                "kind": "spin_down",
                "status": {1: "requested", 2: "success", 3: "error", 4: "stop_pedaling"}.get(
                    raw.action, "reserved"
                ),
            }
        elif raw.opcode == 21:
            details = {"kind": "cadence", "cadenceRpm": operands[0] / 2}
    return {
        "code": raw.opcode if not raw.truncated else None,
        "label": _MACHINE_LABELS.get(raw.opcode, "reserved") if not raw.truncated else "unknown",
        "details": details,
    }
