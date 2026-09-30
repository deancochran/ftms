using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;

namespace DeanCochran.Ftms;

/// <summary>Stable failures for strict wire codecs; malformed evidence is never control permission.</summary>
public enum FtmsError { Length, Kind, Range }

public sealed class FtmsException : ArgumentException
{
    public FtmsError Error { get; }
    public string Code => Error.ToString().ToLowerInvariant();
    public FtmsException(FtmsError error) : base(error.ToString()) => Error = error;
}

/// <summary>Nonthrowing result for expected invalid wire input.</summary>
public sealed class DecodeResult<T> where T : class
{
    public T? Value { get; }
    public FtmsError? Error { get; }
    public bool Success => Error == null;
    internal DecodeResult(T value) => Value = value;
    internal DecodeResult(FtmsError error) => Error = error;
}

/// <summary>Immutable decode diagnostics. A diagnosed value need not be re-encodable.</summary>
public sealed class Diagnostics
{
    public bool Truncated { get; }
    public bool TrailingBytes { get; }
    public bool ReservedFlags { get; }
    public IReadOnlyList<string> Issues { get; }
    public bool IsCanonical => Issues.Count == 0;
    internal Diagnostics(bool truncated = false, bool trailing = false, bool reserved = false,
        params string[] additional)
    {
        Truncated = truncated;
        TrailingBytes = trailing;
        ReservedFlags = reserved;
        var issues = new List<string>();
        if (truncated) issues.Add("truncated");
        if (trailing) issues.Add("trailing_bytes");
        if (reserved) issues.Add("reserved_flags");
        issues.AddRange(additional.Where(s => s.Length != 0));
        Issues = new ReadOnlyCollection<string>(issues.Distinct().ToArray());
    }
}

internal static class Wire
{
    internal static void Require(bool condition, FtmsError error = FtmsError.Range)
    {
        if (!condition) throw new FtmsException(error);
    }

    internal static int Read(ReadOnlySpan<byte> bytes, int offset, int width, bool signed = false)
    {
        if (width == 1) return bytes[offset];
        if (width == 3) return bytes[offset] | bytes[offset + 1] << 8 | bytes[offset + 2] << 16;
        return signed ? BinaryPrimitives.ReadInt16LittleEndian(bytes.Slice(offset, 2))
            : BinaryPrimitives.ReadUInt16LittleEndian(bytes.Slice(offset, 2));
    }

    internal static void Write(Span<byte> bytes, int offset, int value, int width)
    {
        for (int i = 0; i < width; i++) bytes[offset + i] = unchecked((byte)(value >> (8 * i)));
    }

    internal static void Bounds(int value, int width, bool signed = false)
    {
        int max = signed ? short.MaxValue : width == 1 ? byte.MaxValue : width == 2 ? ushort.MaxValue : 0xffffff;
        Require(value >= (signed ? short.MinValue : 0) && value <= max);
    }

    // Encoding finishes and validates before touching a caller's destination.
    internal static bool Copy(byte[] bytes, Span<byte> destination, out int written)
    {
        written = 0;
        if (destination.Length < bytes.Length) return false;
        bytes.CopyTo(destination);
        written = bytes.Length;
        return true;
    }
}
