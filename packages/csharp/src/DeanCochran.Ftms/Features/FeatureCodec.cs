using System;
using System.Buffers.Binary;

namespace DeanCochran.Ftms;

public sealed class Features
{
    public uint MachineRaw { get; }
    public uint TargetRaw { get; }
    public uint MachineUnknown => MachineRaw & ~0x1ffffu;
    public uint TargetUnknown => TargetRaw & ~0x1ffffu;
    public Features(uint machine, uint target) { MachineRaw = machine; TargetRaw = target; }
    public bool Machine(int bit) => bit >= 0 && bit < 32 && (MachineRaw & (1u << bit)) != 0;
    public bool Target(int bit) => bit >= 0 && bit < 32 && (TargetRaw & (1u << bit)) != 0;
}

public static class FeatureCodec
{
    public static Features Decode(ReadOnlySpan<byte> bytes)
    {
        Wire.Require(bytes.Length == 8, FtmsError.Length);
        return new Features(BinaryPrimitives.ReadUInt32LittleEndian(bytes), BinaryPrimitives.ReadUInt32LittleEndian(bytes.Slice(4)));
    }
    public static DecodeResult<Features> TryDecode(ReadOnlySpan<byte> bytes)
    {
        try { return new DecodeResult<Features>(Decode(bytes)); }
        catch (FtmsException e) { return new DecodeResult<Features>(e.Error); }
    }
    public static byte[] Encode(Features value)
    {
        if (value == null) throw new ArgumentNullException(nameof(value));
        var bytes = new byte[8];
        BinaryPrimitives.WriteUInt32LittleEndian(bytes, value.MachineRaw);
        BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(4), value.TargetRaw);
        return bytes;
    }
    public static bool TryEncode(Features value, Span<byte> destination, out int written) => Wire.Copy(Encode(value), destination, out written);
}
