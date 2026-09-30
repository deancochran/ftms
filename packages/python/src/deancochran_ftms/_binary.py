"""Small internal little-endian primitives for fixed-width protocol values."""

from __future__ import annotations

import struct

from ._errors import RawCodecError


def immutable_bytes(value: object) -> bytes:
    """Copy an accepted byte container, rejecting non-byte or non-contiguous views."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, memoryview):
        if (
            value.ndim != 1
            or not value.contiguous
            or value.itemsize != 1
            or value.format
            not in {
                "B",
                "b",
                "c",
            }
        ):
            raise RawCodecError(
                "kind", "input must be a contiguous one-dimensional byte memoryview"
            )
        return value.tobytes()
    raise RawCodecError("kind", "input must be bytes, bytearray, or a byte memoryview")


class Reader:
    """Internal bounds-checked little-endian byte reader."""

    def __init__(self, data: object) -> None:
        self._data = immutable_bytes(data)
        self._offset = 0

    @property
    def length(self) -> int:
        return len(self._data)

    def u8(self) -> int:
        return self._unpack("<B", "uint8")

    def i8(self) -> int:
        return self._unpack("<b", "int8")

    def u16le(self) -> int:
        return self._unpack("<H", "uint16")

    def i16le(self) -> int:
        return self._unpack("<h", "int16")

    def u32le(self) -> int:
        return self._unpack("<I", "uint32")

    def i32le(self) -> int:
        return self._unpack("<i", "int32")

    def _unpack(self, format_: str, name: str) -> int:
        width = struct.calcsize(format_)
        if self._offset + width > len(self._data):
            raise RawCodecError("length", f"truncated {name}")
        result = int(struct.unpack_from(format_, self._data, self._offset)[0])
        self._offset += width
        return result


class Writer:
    """Internal fixed-width little-endian byte writer."""

    def __init__(self) -> None:
        self._data = bytearray()

    def u32le(self, value: int) -> None:
        self._pack("<I", value, 0, 0xFFFFFFFF, "uint32")

    def i16le(self, value: int) -> None:
        self._pack("<h", value, -0x8000, 0x7FFF, "int16")

    def u16le(self, value: int) -> None:
        self._pack("<H", value, 0, 0xFFFF, "uint16")

    def _pack(self, format_: str, value: int, low: int, high: int, name: str) -> None:
        if type(value) is not int or not low <= value <= high:
            raise RawCodecError("range", f"{name} must be an integer from {low} through {high}")
        self._data.extend(struct.pack(format_, value))

    def finish(self) -> bytes:
        return bytes(self._data)
