using System;
using System.Text;

namespace DeanCochran.Ftms;

public sealed class TrainingStatus
{
    public byte Flags { get; }
    public byte Code { get; }
    public bool TextPresent => (Flags & 1) != 0;
    public bool ExtendedString => (Flags & 2) != 0;
    public int ReservedFlags => Flags & 0xfc;
    public int TextOffset { get; }
    public int TextSize => text.Length;
    public byte[] TextBytes => (byte[])text.Clone();
    public string? Text => TextPresent ? Encoding.UTF8.GetString(text) : null;
    public Diagnostics Diagnostics { get; }
    private readonly byte[] text;
    public TrainingStatus(byte flags, byte code, string? text = null)
    {
        Flags = flags; Code = code;
        try { this.text = text == null ? Array.Empty<byte>() : new UTF8Encoding(false, true).GetBytes(text); }
        catch (EncoderFallbackException) { throw new FtmsException(FtmsError.Range); }
        TextOffset = TextPresent ? 2 : 0; Diagnostics = new Diagnostics();
    }
    internal TrainingStatus(byte flags, byte code, byte[] text, int offset, Diagnostics diagnostics)
    { Flags = flags; Code = code; this.text = (byte[])text.Clone(); TextOffset = offset; Diagnostics = diagnostics; }
}

public sealed class MachineStatus
{
    public byte Opcode { get; }
    public byte Action { get; }
    public ControlRequest? Parameter { get; }
    public Diagnostics Diagnostics { get; }
    private readonly byte[] raw;
    public byte[] RawBytes => (byte[])raw.Clone();
    public MachineStatus(byte opcode, byte action = 0, ControlRequest? parameter = null)
        : this(opcode, action, parameter, new Diagnostics(), Array.Empty<byte>()) { }
    internal MachineStatus(byte opcode, byte action, ControlRequest? parameter, Diagnostics diagnostics, byte[] raw)
    { Opcode = opcode; Action = action; Parameter = parameter; Diagnostics = diagnostics; this.raw = (byte[])raw.Clone(); }
}

public static class StatusCodec
{
    private static int Length(byte op) => op switch
    {
        1 or 3 or 4 or 255 => 1, 2 or 9 or 20 => 2, 13 => 4, 15 => 5,
        16 or 18 => 7, 17 => 11, >= 5 and <= 8 or >= 10 and <= 12 or 14 or 19 or 21 => 3, _ => 0
    };
    private static int Mapped(byte op) => op >= 5 && op <= 9 ? op - 3 : op >= 10 && op <= 19 || op == 21 ? op - 1 : -1;

    public static TrainingStatus DecodeTraining(ReadOnlySpan<byte> bytes)
    {
        if (bytes.Length < 2) return new TrainingStatus(bytes.Length == 0 ? (byte)0 : bytes[0], 0, Array.Empty<byte>(), 0, new Diagnostics(truncated: true));
        byte flags = bytes[0], code = bytes[1];
        bool present = (flags & 1) != 0, invalidUtf8 = false;
        byte[] text = present ? bytes.Slice(2).ToArray() : Array.Empty<byte>();
        try { _ = new UTF8Encoding(false, true).GetString(text); }
        catch (DecoderFallbackException) { invalidUtf8 = true; }
        var diagnostics = new Diagnostics(false, !present && bytes.Length > 2, (flags & 0xfc) != 0,
            code > 15 ? "reserved_value" : "", (flags & 2) != 0 && !present ? "invalid_flags" : "", invalidUtf8 ? "invalid_utf8" : "");
        return new TrainingStatus(flags, code, text, present ? 2 : 0, diagnostics);
    }

    public static byte[] EncodeTraining(TrainingStatus value)
    {
        if (value == null) throw new ArgumentNullException(nameof(value));
        Wire.Require(value.Diagnostics.IsCanonical && value.Code <= 15 && value.ReservedFlags == 0 && (!value.ExtendedString || value.TextPresent));
        Wire.Require(value.TextPresent || value.TextSize == 0);
        byte[] text = value.TextBytes;
        var bytes = new byte[2 + text.Length]; bytes[0] = value.Flags; bytes[1] = value.Code;
        text.CopyTo(bytes, 2);
        return bytes;
    }

    public static MachineStatus DecodeMachine(ReadOnlySpan<byte> bytes)
    {
        if (bytes.IsEmpty) return new MachineStatus(0, 0, null, new Diagnostics(true, false, false, "unknown_opcode"), Array.Empty<byte>());
        byte op = bytes[0]; int length = Length(op);
        if (length == 0) return new MachineStatus(op, 0, null, new Diagnostics(false, false, false, "unknown_opcode"), bytes.ToArray());
        if (bytes.Length < length) return new MachineStatus(op, 0, null, new Diagnostics(truncated: true), bytes.ToArray());
        byte action = op == 2 || op == 20 ? bytes[1] : (byte)0;
        bool reserved = op == 2 && (action < 1 || action > 2) || op == 20 && (action < 1 || action > 4);
        int mapped = Mapped(op);
        ControlRequest? parameter = null;
        if (mapped >= 0)
        {
            // Machine Status resistance always uses signed 16-bit tenths,
            // independently of any selected Control Point request profile.
            var request = bytes.Slice(0, length).ToArray(); request[0] = (byte)mapped;
            parameter = ControlCodec.DecodeRequest(request);
        }
        return new MachineStatus(op, action, parameter,
            new Diagnostics(false, bytes.Length > length, false, reserved ? "reserved_value" : ""), bytes.ToArray());
    }

    public static byte[] EncodeMachine(MachineStatus value)
    {
        if (value == null) throw new ArgumentNullException(nameof(value));
        int length = Length(value.Opcode), mapped = Mapped(value.Opcode);
        Wire.Require(length != 0 && value.Diagnostics.IsCanonical);
        Wire.Require(mapped >= 0 ? value.Parameter?.Opcode == mapped : value.Parameter == null);
        if (value.Opcode == 2) Wire.Require(value.Action >= 1 && value.Action <= 2);
        else if (value.Opcode == 20) Wire.Require(value.Action >= 1 && value.Action <= 4);
        else Wire.Require(value.Action == 0);
        byte[] bytes = value.Parameter != null ? ControlCodec.EncodeRequest(value.Parameter) : new byte[length];
        Wire.Require(bytes.Length == length);
        bytes[0] = value.Opcode;
        if (value.Opcode == 2 || value.Opcode == 20) bytes[1] = value.Action;
        return bytes;
    }
    public static bool TryEncodeTraining(TrainingStatus value, Span<byte> destination, out int written) => Wire.Copy(EncodeTraining(value), destination, out written);
    public static bool TryEncodeMachine(MachineStatus value, Span<byte> destination, out int written) => Wire.Copy(EncodeMachine(value), destination, out written);
}
