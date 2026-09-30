from __future__ import annotations

import pytest

from deancochran_ftms import RawCodecError
from deancochran_ftms._binary import Reader, Writer, immutable_bytes


def test_reader_writer_little_endian_and_uint32_bounds() -> None:
    writer = Writer()
    writer.u16le(0x3412)
    writer.i16le(-2)
    writer.u32le(0x78563412)
    assert writer.finish() == b"\x12\x34\xfe\xff\x12\x34\x56\x78"
    reader = Reader(writer.finish())
    assert reader.u16le() == 0x3412
    assert reader.i16le() == -2
    assert reader.u32le() == 0x78563412
    for value in (-1, 0x1_0000_0000, True):
        with pytest.raises(RawCodecError, match="uint32"):
            Writer().u32le(value)


def test_reader_rejects_truncation() -> None:
    with pytest.raises(RawCodecError, match="truncated"):
        Reader(b"\x00\x00\x00").u32le()


def test_reader_handles_signed_and_unsigned_widths() -> None:
    reader = Reader(b"\xff\x80\xff\xff\xff\xff\xff\xff")
    assert reader.u8() == 255
    assert reader.i8() == -128
    assert reader.i16le() == -1
    assert reader.i32le() == -1


def test_byte_inputs_are_copied_and_views_must_be_contiguous_1d_bytes() -> None:
    source = bytearray(b"\x01")
    copied = immutable_bytes(source)
    source[0] = 2
    assert copied == b"\x01"
    assert immutable_bytes(memoryview(bytearray(b"\x03"))) == b"\x03"
    with pytest.raises(RawCodecError):
        immutable_bytes(memoryview(bytearray(b"\x00\x00\x00\x00"))[::2])
