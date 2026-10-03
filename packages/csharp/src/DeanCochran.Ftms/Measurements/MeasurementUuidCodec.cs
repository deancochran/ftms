using System;
using System.Collections.Generic;

namespace DeanCochran.Ftms;

/// <summary>Whether a UUID identifies one of the six FTMS machine-data layouts.</summary>
public enum MeasurementUuidDecodeStatus { Known, Unsupported }

/// <summary>
/// UUID-selected measurement evidence. A known result exposes the established
/// raw measurement, normalized view, and diagnostics without BLE dependencies
/// or packet-shape inference.
/// </summary>
public sealed class MeasurementUuidDecodeResult
{
    public MeasurementUuidDecodeStatus Status { get; }
    /// <summary>Canonical lowercase, undashed full Bluetooth UUID.</summary>
    public string CharacteristicUuid { get; }
    public MeasurementKind? Kind { get; }
    public Measurement? Measurement { get; }
    public NormalizedMeasurement? Normalized => Measurement?.Normalized;
    public Diagnostics? Diagnostics => Measurement?.Diagnostics;

    private MeasurementUuidDecodeResult(string uuid)
    { Status = MeasurementUuidDecodeStatus.Unsupported; CharacteristicUuid = uuid; }
    private MeasurementUuidDecodeResult(string uuid, Measurement measurement)
    { Status = MeasurementUuidDecodeStatus.Known; CharacteristicUuid = uuid; Measurement = measurement; Kind = measurement.Kind; }

    internal static MeasurementUuidDecodeResult Unsupported(string uuid) => new MeasurementUuidDecodeResult(uuid);
    internal static MeasurementUuidDecodeResult Known(string uuid, Measurement measurement) => new MeasurementUuidDecodeResult(uuid, measurement);
}

/// <summary>
/// Pure UUID dispatch for FTMS measurement data. Standard 16-bit aliases are
/// accepted; full UUIDs must use the Bluetooth base UUID, so vendor UUIDs do
/// not select a layout merely because their bytes resemble one.
/// </summary>
public static class MeasurementUuidCodec
{
    private const string Suffix = "00001000800000805f9b34fb";

    /// <summary>Decode one known measurement UUID or return an explicit unsupported result.</summary>
    public static MeasurementUuidDecodeResult Decode(string characteristicUuid, ReadOnlySpan<byte> bytes, MeasurementFormat? format = null)
    {
        if (characteristicUuid == null) throw new ArgumentNullException(nameof(characteristicUuid));
        string uuid = Normalize(characteristicUuid);
        if (!TryGetKind(uuid, out MeasurementKind kind)) return MeasurementUuidDecodeResult.Unsupported(uuid);
        format ??= new MeasurementFormat();
        try
        {
            return MeasurementUuidDecodeResult.Known(uuid, MeasurementCodec.Decode(kind, bytes, format));
        }
        catch (FtmsException error) when (error.Error == FtmsError.Length)
        {
            // The known UUID still identifies its layout even if its flag word is incomplete.
            return MeasurementUuidDecodeResult.Known(uuid, new Measurement(kind, 0,
                new Dictionary<MeasurementField, int?>(), format, new Diagnostics(truncated: true), 0));
        }
    }

    private static bool TryGetKind(string uuid, out MeasurementKind kind)
    {
        kind = default;
        if (uuid.Length != 32 || !uuid.StartsWith("0000", StringComparison.Ordinal) ||
            !uuid.EndsWith(Suffix, StringComparison.Ordinal)) return false;
        int value;
        try { value = Convert.ToInt32(uuid.Substring(4, 4), 16); }
        catch (FormatException) { return false; }
        if (value < 0x2acd || value > 0x2ad2) return false;
        kind = (MeasurementKind)(value - 0x2acd);
        return true;
    }

    private static string Normalize(string uuid)
    {
        string value = uuid.Trim().ToLowerInvariant();
        string shortValue = value.StartsWith("0x", StringComparison.Ordinal) ? value.Substring(2) : value;
        if (shortValue.Length == 4 && IsHex(shortValue)) return "0000" + shortValue + Suffix;
        if (value.Length == 36 && value[8] == '-' && value[13] == '-' && value[18] == '-' && value[23] == '-')
        {
            string compact = value.Replace("-", string.Empty);
            if (compact.Length == 32 && IsHex(compact)) return compact;
        }
        return value;
    }

    private static bool IsHex(string value)
    {
        foreach (char c in value)
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
        return true;
    }
}
