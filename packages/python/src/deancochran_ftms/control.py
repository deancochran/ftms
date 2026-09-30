"""Strict bidirectional FTMS Control Point raw codecs."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Literal, cast

from ._binary import immutable_bytes
from ._errors import RawCodecError


@dataclass(frozen=True, slots=True)
class ControlFormatOptions:
    resistance_format: str = "signed16Tenths"


@dataclass(frozen=True, slots=True)
class ControlRequestRaw:
    opcode: int
    operands: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ControlResponseRaw:
    request_opcode: int
    result_code: int
    parameter: int = 0
    low: int = 0
    high: int = 0
    unknown_request: int = 0
    unknown_result: int = 0
    unexpected_parameters: int = 0


_COUNTS = (0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 2, 3, 5, 4, 1, 1, 1)


def _opt(o: ControlFormatOptions | None) -> Literal["signed16Tenths", "uint8Tenths"]:
    if o is None:
        return "signed16Tenths"
    if not isinstance(o, ControlFormatOptions) or o.resistance_format not in (
        "signed16Tenths",
        "uint8Tenths",
    ):
        raise RawCodecError("kind", "Unsupported Control Point resistance format")
    return cast(Literal["signed16Tenths", "uint8Tenths"], o.resistance_format)


def _len(op: int, opt: str) -> int:
    if not 0 <= op <= 20:
        raise RawCodecError("kind", "Unknown Control Point request opcode")
    return (
        2
        if op == 4 and opt == "uint8Tenths"
        else (1, 1, 3, 3, 3, 3, 2, 1, 2, 3, 3, 3, 4, 3, 5, 7, 11, 7, 3, 2, 3)[op]
    )


def _checkint(v: object, lo: int, hi: int) -> int:
    if type(v) is not int or not lo <= v <= hi:
        raise RawCodecError("range", f"integer must be {lo} through {hi}")
    return v


def _ranges(op: int, opt: str) -> list[tuple[int, int]]:
    if op == 17:
        return [(-32768, 32767), (-32768, 32767), (0, 255), (0, 255)]
    if op == 12:
        return [(0, 0xFFFFFF)]
    if op == 4:
        return [(0, 255) if opt == "uint8Tenths" else (-32768, 32767)]
    if op in (3, 5):
        return [(-32768, 32767)]
    if op in (6, 8, 19):
        return [(0, 255)]
    return [(0, 65535)] * _COUNTS[op]


def encode_control_request_raw(
    request: ControlRequestRaw, options: ControlFormatOptions | None = None
) -> bytes:
    opt = _opt(options)
    if not isinstance(request, ControlRequestRaw):
        raise RawCodecError("kind", "ControlRequestRaw value is required")
    op = _checkint(request.opcode, 0, 255)
    _len(op, opt)
    if not isinstance(request.operands, tuple) or len(request.operands) != _COUNTS[op]:
        raise RawCodecError("length", "wrong operand count")
    v = [_checkint(x, *r) for x, r in zip(request.operands, _ranges(op, opt), strict=True)]
    if op in (8, 19) and v[0] not in (1, 2):
        raise RawCodecError("range", "action must be 1 or 2")
    b = bytearray([op])
    fmts = {
        2: "<H",
        3: "<h",
        4: "<h",
        5: "<h",
        6: "<B",
        8: "<B",
        9: "<H",
        10: "<H",
        11: "<H",
        13: "<H",
        18: "<H",
        19: "<B",
        20: "<H",
    }
    if op == 4 and opt == "uint8Tenths":
        b.extend(struct.pack("<B", v[0]))
    elif op == 12:
        b.extend(bytes((v[0] & 255, v[0] >> 8 & 255, v[0] >> 16)))
    elif op in (14, 15, 16):
        b.extend(struct.pack("<" + "H" * len(v), *v))
    elif op == 17:
        b.extend(struct.pack("<hhBB", *v))
    elif op in fmts:
        b.extend(struct.pack(fmts[op], v[0]))
    return bytes(b)


def decode_control_request_raw(
    data: bytes | bytearray | memoryview, options: ControlFormatOptions | None = None
) -> ControlRequestRaw:
    opt = _opt(options)
    b = immutable_bytes(data)
    if not b:
        raise RawCodecError("length", "Control Point request requires an opcode")
    op = b[0]
    n = _len(op, opt)
    if len(b) != n:
        raise RawCodecError("length", f"Opcode {op} requires exactly {n} bytes")
    if op in (0, 1, 7):
        v: tuple[int, ...] = ()
    elif op == 4:
        v = (struct.unpack("<B" if opt == "uint8Tenths" else "<h", b[1:])[0],)
    elif op in (2, 9, 10, 11, 13, 18, 20):
        v = (struct.unpack("<H", b[1:])[0],)
    elif op in (3, 5):
        v = (struct.unpack("<h", b[1:])[0],)
    elif op in (6, 8, 19):
        v = (b[1],)
    elif op == 12:
        v = (b[1] | b[2] << 8 | b[3] << 16,)
    elif op in (14, 15, 16):
        v = struct.unpack("<" + "H" * _COUNTS[op], b[1:])
    else:
        v = struct.unpack("<hhBB", b[1:])
    if op in (8, 19) and v[0] not in (1, 2):
        raise RawCodecError("range", "action must be 1 or 2")
    return ControlRequestRaw(op, tuple(v))


def decode_control_response_raw(data: bytes | bytearray | memoryview) -> ControlResponseRaw:
    b = immutable_bytes(data)
    if len(b) < 3:
        raise RawCodecError("length", "Control Point response requires at least three bytes")
    if b[0] != 128:
        raise RawCodecError("kind", "Payload is not a Control Point response")
    op, result = b[1], b[2]
    if op == 19 and result == 1 and len(b) not in (3, 7):
        raise RawCodecError("length", "successful spin down response must be 3 or 7 bytes")
    if op == 19 and result == 1 and len(b) == 7:
        low, high = struct.unpack("<HH", b[3:])
        return ControlResponseRaw(
            op, result, 1, low, high, int(op > 20), int(not 1 <= result <= 5), 0
        )
    return ControlResponseRaw(
        op, result, 0, 0, 0, int(op > 20), int(not 1 <= result <= 5), int(len(b) > 3)
    )


def encode_control_response_raw(r: ControlResponseRaw) -> bytes:
    if not isinstance(r, ControlResponseRaw):
        raise RawCodecError("kind", "ControlResponseRaw value is required")
    op = _checkint(r.request_opcode, 0, 255)
    result = _checkint(r.result_code, 1, 5)
    p = _checkint(r.parameter, 0, 1)
    low = _checkint(r.low, 0, 65535)
    high = _checkint(r.high, 0, 65535)
    flags = (r.unknown_request, r.unknown_result, r.unexpected_parameters)
    if (
        any(type(x) is not int or x not in (0, 1) for x in flags)
        or r.unknown_request != int(op > 20)
        or r.unknown_result
        or r.unexpected_parameters
    ):
        raise RawCodecError("range", "noncanonical response diagnostics")
    if op > 20 and result != 2:
        raise RawCodecError("kind", "unknown request must be not supported")
    if p and (op != 19 or result != 1):
        raise RawCodecError("range", "spin-down parameter requires successful spin-down")
    if not p and (low or high):
        raise RawCodecError("range", "no parameter requires zero values")
    return bytes((128, op, result)) + (struct.pack("<HH", low, high) if p else b"")
