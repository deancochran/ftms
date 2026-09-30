using System;
using System.Collections.Generic;

namespace DeanCochran.Ftms;

public enum ControlOpcode : byte
{
    RequestControl, Reset, TargetSpeed, TargetInclination, TargetResistance, TargetPower,
    TargetHeartRate, StartResume, StopPause, TargetedEnergy, TargetedSteps, TargetedStrides,
    TargetedDistance, TargetedTrainingTime, TargetedTimeTwoHrZones, TargetedTimeThreeHrZones,
    TargetedTimeFiveHrZones, IndoorBikeSimulation, WheelCircumference, SpinDown, TargetedCadence
}
public enum ControlResistanceFormat { SInt16Tenths, UInt8Tenths }

/// <summary>Raw operands in opcode-defined wire order and units. Input is copied.</summary>
public sealed class ControlRequest
{
    public byte Opcode { get; }
    public IReadOnlyList<int> Operands { get; }
    public ControlRequest(byte opcode, params int[] operands)
    {
        Opcode = opcode;
        Operands = Array.AsReadOnly((int[])(operands ?? throw new ArgumentNullException(nameof(operands))).Clone());
    }
    public ControlRequest(ControlOpcode opcode, params int[] operands) : this((byte)opcode, operands) { }
}

public sealed class ControlResponse
{
    public byte RequestOpcode { get; }
    public byte ResultCode { get; }
    public ushort? SpinDownStartSpeed { get; }
    public ushort? SpinDownEndSpeed { get; }
    public bool UnknownRequest => RequestOpcode > 20;
    public bool UnknownResult => ResultCode < 1 || ResultCode > 5;
    public bool UnexpectedParameters => parameters.Length != 0;
    private readonly byte[] parameters;
    public byte[] UnexpectedParameterBytes => (byte[])parameters.Clone();
    public ControlResponse(byte requestOpcode, byte resultCode, ushort? spinDownStartSpeed = null, ushort? spinDownEndSpeed = null)
        : this(requestOpcode, resultCode, spinDownStartSpeed, spinDownEndSpeed, Array.Empty<byte>()) { }
    internal ControlResponse(byte op, byte result, ushort? low, ushort? high, byte[] extra)
    { RequestOpcode = op; ResultCode = result; SpinDownStartSpeed = low; SpinDownEndSpeed = high; parameters = (byte[])extra.Clone(); }
}

public static class ControlCodec
{
    private static readonly int[] Counts = { 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 2, 3, 5, 4, 1, 1, 1 };
    internal static (int width, bool signed) Operand(byte op, int index, ControlResistanceFormat format) => op switch
    {
        3 or 5 => (2, true),
        4 => format == ControlResistanceFormat.UInt8Tenths ? (1, false) : (2, true),
        6 or 8 or 19 => (1, false),
        12 => (3, false),
        17 => index < 2 ? (2, true) : (1, false),
        _ => (2, false)
    };
    private static void ValidateFormat(ControlResistanceFormat format) => Wire.Require(
        format == ControlResistanceFormat.SInt16Tenths || format == ControlResistanceFormat.UInt8Tenths, FtmsError.Kind);

    public static ControlRequest DecodeRequest(ReadOnlySpan<byte> bytes, ControlResistanceFormat format = ControlResistanceFormat.SInt16Tenths)
    {
        ValidateFormat(format);
        Wire.Require(bytes.Length > 0, FtmsError.Length);
        byte op = bytes[0];
        Wire.Require(op < Counts.Length, FtmsError.Kind);
        int length = 1;
        for (int i = 0; i < Counts[op]; i++) length += Operand(op, i, format).width;
        Wire.Require(bytes.Length == length, FtmsError.Length);
        var values = new int[Counts[op]];
        int at = 1;
        for (int i = 0; i < values.Length; i++)
        {
            var f = Operand(op, i, format);
            values[i] = Wire.Read(bytes, at, f.width, f.signed); at += f.width;
        }
        if (op == 8 || op == 19) Wire.Require(values[0] == 1 || values[0] == 2);
        return new ControlRequest(op, values);
    }

    public static DecodeResult<ControlRequest> TryDecodeRequest(ReadOnlySpan<byte> bytes, ControlResistanceFormat format = ControlResistanceFormat.SInt16Tenths)
    {
        try { return new DecodeResult<ControlRequest>(DecodeRequest(bytes, format)); }
        catch (FtmsException e) { return new DecodeResult<ControlRequest>(e.Error); }
    }

    public static byte[] EncodeRequest(ControlRequest value, ControlResistanceFormat format = ControlResistanceFormat.SInt16Tenths)
    {
        if (value == null) throw new ArgumentNullException(nameof(value));
        ValidateFormat(format);
        byte op = value.Opcode;
        Wire.Require(op < Counts.Length, FtmsError.Kind);
        Wire.Require(value.Operands.Count == Counts[op], FtmsError.Length);
        if (op == 8 || op == 19) Wire.Require(value.Operands[0] == 1 || value.Operands[0] == 2);
        int length = 1;
        for (int i = 0; i < value.Operands.Count; i++)
        {
            var f = Operand(op, i, format);
            Wire.Bounds(value.Operands[i], f.width, f.signed); length += f.width;
        }
        var bytes = new byte[length]; bytes[0] = op;
        int at = 1;
        for (int i = 0; i < value.Operands.Count; i++)
        {
            var f = Operand(op, i, format);
            Wire.Write(bytes, at, value.Operands[i], f.width); at += f.width;
        }
        return bytes;
    }

    public static bool TryEncodeRequest(ControlRequest value, Span<byte> destination, out int written, ControlResistanceFormat format = ControlResistanceFormat.SInt16Tenths) =>
        Wire.Copy(EncodeRequest(value, format), destination, out written);

    public static ControlResponse DecodeResponse(ReadOnlySpan<byte> bytes)
    {
        Wire.Require(bytes.Length >= 3, FtmsError.Length);
        Wire.Require(bytes[0] == 0x80, FtmsError.Kind);
        byte op = bytes[1], result = bytes[2];
        bool spin = op == 19 && result == 1;
        if (spin) Wire.Require(bytes.Length == 3 || bytes.Length == 7, FtmsError.Length);
        return spin && bytes.Length == 7
            ? new ControlResponse(op, result, (ushort)Wire.Read(bytes, 3, 2), (ushort)Wire.Read(bytes, 5, 2))
            : new ControlResponse(op, result, null, null, bytes.Slice(3).ToArray());
    }

    public static DecodeResult<ControlResponse> TryDecodeResponse(ReadOnlySpan<byte> bytes)
    {
        try { return new DecodeResult<ControlResponse>(DecodeResponse(bytes)); }
        catch (FtmsException e) { return new DecodeResult<ControlResponse>(e.Error); }
    }

    public static byte[] EncodeResponse(ControlResponse value)
    {
        if (value == null) throw new ArgumentNullException(nameof(value));
        Wire.Require(!value.UnknownResult && !value.UnexpectedParameters);
        Wire.Require(!value.UnknownRequest || value.ResultCode == 2, FtmsError.Kind);
        bool spin = value.SpinDownStartSpeed.HasValue;
        Wire.Require(spin == value.SpinDownEndSpeed.HasValue);
        Wire.Require(!spin || value.RequestOpcode == 19 && value.ResultCode == 1);
        var bytes = new byte[spin ? 7 : 3];
        bytes[0] = 0x80; bytes[1] = value.RequestOpcode; bytes[2] = value.ResultCode;
        if (spin) { Wire.Write(bytes, 3, value.SpinDownStartSpeed!.Value, 2); Wire.Write(bytes, 5, value.SpinDownEndSpeed!.Value, 2); }
        return bytes;
    }
    public static bool TryEncodeResponse(ControlResponse value, Span<byte> destination, out int written) => Wire.Copy(EncodeResponse(value), destination, out written);
}
