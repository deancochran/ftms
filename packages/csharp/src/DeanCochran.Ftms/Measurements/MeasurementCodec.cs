using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;

namespace DeanCochran.Ftms;

public enum MeasurementKind { Treadmill, CrossTrainer, StepClimber, StairClimber, Rower, IndoorBike }
public enum MeasurementField
{
    Speed, AverageSpeed, Distance, Inclination, RampAngle, PositiveElevation, NegativeElevation,
    InstantaneousPace, AveragePace, TotalEnergy, EnergyPerHour, EnergyPerMinute, HeartRate,
    MetabolicEquivalent, ElapsedTime, RemainingTime, ForceOnBelt, Power, StepRate, AverageStepRate,
    StrideCount, Resistance, AveragePower, FloorCount, StepCount, StrokeRate, StrokeCount,
    AverageStrokeRate, Cadence, AverageCadence
}
public enum TreadmillPaceFormat { UInt16, UInt8Legacy }

/// <summary>Explicit independent wire choices. Never selected from packet length or device identity.</summary>
public sealed class MeasurementFormat
{
    public ResistanceFormat Resistance { get; }
    public TreadmillPaceFormat TreadmillPace { get; }
    public MeasurementFormat(ResistanceFormat resistance = ResistanceFormat.UInt8Whole, TreadmillPaceFormat treadmillPace = TreadmillPaceFormat.UInt16)
    { Resistance = resistance; TreadmillPace = treadmillPace; }
    internal void Validate()
    {
        Wire.Require(Resistance == ResistanceFormat.UInt8Whole || Resistance == ResistanceFormat.SInt16Tenths, FtmsError.Kind);
        Wire.Require(TreadmillPace == TreadmillPaceFormat.UInt16 || TreadmillPace == TreadmillPaceFormat.UInt8Legacy, FtmsError.Kind);
    }
}

/// <summary>Immutable raw evidence. A present null value is an unavailable sentinel; an absent key was not read.</summary>
public sealed class Measurement
{
    public MeasurementKind Kind { get; }
    public uint Flags { get; }
    public IReadOnlyDictionary<MeasurementField, int?> Fields { get; }
    public Diagnostics Diagnostics { get; }
    public int BytesRead { get; }
    public MeasurementFormat Format { get; }
    public bool MoreData => (Flags & 1) != 0;
    public bool Backward => Kind == MeasurementKind.CrossTrainer && (Flags & 0x8000) != 0;
    public NormalizedMeasurement Normalized => new NormalizedMeasurement(this);

    public Measurement(MeasurementKind kind, uint flags, IReadOnlyDictionary<MeasurementField, int?> fields, MeasurementFormat? format = null)
        : this(kind, flags, fields, format ?? new MeasurementFormat(), new Diagnostics(), 0) { }
    internal Measurement(MeasurementKind kind, uint flags, IReadOnlyDictionary<MeasurementField, int?> fields,
        MeasurementFormat format, Diagnostics diagnostics, int bytesRead)
    {
        if (fields == null) throw new ArgumentNullException(nameof(fields));
        Kind = kind; Flags = flags; Format = format; Diagnostics = diagnostics; BytesRead = bytesRead;
        var copy = new Dictionary<MeasurementField, int?>();
        foreach (var field in fields) copy.Add(field.Key, field.Value);
        Fields = new ReadOnlyDictionary<MeasurementField, int?>(copy);
    }
}

/// <summary>Stateless FTMS measurement codec; More Data packets are not assembled or scheduled.</summary>
public static class MeasurementCodec
{
    private sealed class Field
    {
        internal readonly int Bit, Width;
        internal readonly MeasurementField Index;
        internal readonly bool Signed, Sentinel;
        internal Field(int bit, int width, int index, bool signed = false, bool sentinel = false)
        { Bit = bit; Width = width; Index = (MeasurementField)index; Signed = signed; Sentinel = sentinel; }
    }
    private sealed class Layout
    {
        internal readonly int FlagBytes;
        internal readonly uint ValidFlags;
        internal readonly Field[] Fields;
        internal Layout(int flagBytes, uint validFlags, params Field[] fields)
        { FlagBytes = flagBytes; ValidFlags = validFlags; Fields = fields; }
    }
    private static Field F(int bit, int width, int index, bool signed = false, bool sentinel = false) => new Field(bit, width, index, signed, sentinel);
    // Specification-ordered fields; shared flags deliberately cover multiple adjacent fields.
    private static readonly Layout[] Layouts =
    {
        new Layout(2, 0x1fff,
            F(0,2,0), F(1,2,1), F(2,3,2), F(3,2,3,true,true), F(3,2,4,true,true),
            F(4,2,5), F(4,2,6), F(5,2,7), F(6,2,8), F(7,2,9,false,true),
            F(7,2,10,false,true), F(7,1,11,false,true), F(8,1,12), F(9,1,13),
            F(10,2,14), F(11,2,15), F(12,2,16,true,true), F(12,2,17,true,true)),
        new Layout(3, 0xffff,
            F(0,2,0), F(1,2,1), F(2,3,2), F(3,2,18,false,true), F(3,2,19,false,true),
            F(4,2,20), F(5,2,5), F(5,2,6), F(6,2,3,true,true), F(6,2,4,true,true),
            F(7,1,21), F(8,2,17,true), F(9,2,22,true), F(10,2,9,false,true),
            F(10,2,10,false,true), F(10,1,11,false,true), F(11,1,12), F(12,1,13), F(13,2,14), F(14,2,15)),
        new Layout(2, 0x01ff,
            F(0,2,23), F(0,2,24), F(1,2,18), F(2,2,19), F(3,2,5),
            F(4,2,9,false,true), F(4,2,10,false,true), F(4,1,11,false,true), F(5,1,12), F(6,1,13), F(7,2,14), F(8,2,15)),
        new Layout(2, 0x03ff,
            F(0,2,23), F(1,2,18), F(2,2,19), F(3,2,5), F(4,2,20),
            F(5,2,9,false,true), F(5,2,10,false,true), F(5,1,11,false,true), F(6,1,12), F(7,1,13), F(8,2,14), F(9,2,15)),
        new Layout(2, 0x1fff,
            F(0,1,25), F(0,2,26), F(1,1,27), F(2,3,2), F(3,2,7), F(4,2,8),
            F(5,2,17,true), F(6,2,22,true), F(7,1,21), F(8,2,9,false,true),
            F(8,2,10,false,true), F(8,1,11,false,true), F(9,1,12), F(10,1,13), F(11,2,14), F(12,2,15)),
        new Layout(2, 0x1fff,
            F(0,2,0), F(1,2,1), F(2,2,28), F(3,2,29), F(4,3,2), F(5,1,21),
            F(6,2,17,true), F(7,2,22,true), F(8,2,9,false,true), F(8,2,10,false,true),
            F(8,1,11,false,true), F(9,1,12), F(10,1,13), F(11,2,14), F(12,2,15))
    };
    private static Layout GetLayout(MeasurementKind kind)
    { Wire.Require((uint)kind < (uint)Layouts.Length, FtmsError.Kind); return Layouts[(int)kind]; }
    private static Field SelectedFormat(MeasurementKind kind, Field field, MeasurementFormat format)
    {
        if (field.Index == MeasurementField.Resistance && format.Resistance == ResistanceFormat.SInt16Tenths)
            return F(field.Bit, 2, (int)field.Index, true);
        if (kind == MeasurementKind.Treadmill && (field.Index == MeasurementField.InstantaneousPace || field.Index == MeasurementField.AveragePace)
            && format.TreadmillPace == TreadmillPaceFormat.UInt8Legacy) return F(field.Bit, 1, (int)field.Index);
        return field;
    }
    private static bool Selected(uint flags, Field field) => field.Bit == 0 ? (flags & 1) == 0 : (flags & (1u << field.Bit)) != 0;
    private static int Sentinel(Field field) => field.Signed ? 0x7fff : field.Width == 1 ? 0xff : 0xffff;

    public static Measurement Decode(MeasurementKind kind, ReadOnlySpan<byte> bytes, MeasurementFormat? format = null)
    {
        format ??= new MeasurementFormat(); format.Validate();
        var layout = GetLayout(kind);
        Wire.Require(bytes.Length >= layout.FlagBytes, FtmsError.Length);
        uint flags = (uint)Wire.Read(bytes, 0, layout.FlagBytes);
        var fields = new Dictionary<MeasurementField, int?>();
        int at = layout.FlagBytes;
        bool truncated = false, unavailable = false;
        foreach (var original in layout.Fields)
        {
            var field = SelectedFormat(kind, original, format);
            if (!Selected(flags, field)) continue;
            if (at + field.Width > bytes.Length) { truncated = true; break; }
            int raw = Wire.Read(bytes, at, field.Width);
            at += field.Width;
            if (field.Sentinel && raw == Sentinel(field)) { fields.Add(field.Index, null); unavailable = true; }
            else fields.Add(field.Index, field.Signed && raw > 0x7fff ? raw - 0x10000 : raw);
        }
        var diagnostics = new Diagnostics(truncated, !truncated && at < bytes.Length, (flags & ~layout.ValidFlags) != 0,
            (flags & 1) != 0 ? "more_data" : "", unavailable ? "unavailable" : "");
        return new Measurement(kind, flags, fields, format, diagnostics, at);
    }

    public static DecodeResult<Measurement> TryDecode(MeasurementKind kind, ReadOnlySpan<byte> bytes, MeasurementFormat? format = null)
    {
        try { return new DecodeResult<Measurement>(Decode(kind, bytes, format)); }
        catch (FtmsException e) { return new DecodeResult<Measurement>(e.Error); }
    }

    public static byte[] Encode(Measurement value)
    {
        if (value == null) throw new ArgumentNullException(nameof(value));
        value.Format.Validate();
        var layout = GetLayout(value.Kind);
        Wire.Require(!value.Diagnostics.Truncated && !value.Diagnostics.TrailingBytes && !value.Diagnostics.ReservedFlags);
        Wire.Require((value.Flags & ~layout.ValidFlags) == 0);
        int length = layout.FlagBytes, count = 0;
        foreach (var original in layout.Fields)
        {
            if (!Selected(value.Flags, original)) continue;
            var field = SelectedFormat(value.Kind, original, value.Format);
            Wire.Require(value.Fields.TryGetValue(field.Index, out int? raw));
            if (!raw.HasValue) Wire.Require(field.Sentinel);
            else { Wire.Bounds(raw.Value, field.Width, field.Signed); Wire.Require(!field.Sentinel || raw.Value != Sentinel(field)); }
            length += field.Width; count++;
        }
        Wire.Require(count == value.Fields.Count);
        var bytes = new byte[length]; Wire.Write(bytes, 0, (int)value.Flags, layout.FlagBytes);
        int at = layout.FlagBytes;
        foreach (var original in layout.Fields)
        {
            if (!Selected(value.Flags, original)) continue;
            var field = SelectedFormat(value.Kind, original, value.Format);
            Wire.Write(bytes, at, value.Fields[field.Index] ?? Sentinel(field), field.Width); at += field.Width;
        }
        return bytes;
    }
    public static bool TryEncode(Measurement value, Span<byte> destination, out int written) => Wire.Copy(Encode(value), destination, out written);
}

/// <summary>Physical-unit projections. Raw Fields retain absence versus unavailable evidence.</summary>
public sealed class NormalizedMeasurement
{
    private readonly Measurement value;
    internal NormalizedMeasurement(Measurement value) => this.value = value;
    public double? GetValue(MeasurementField field)
    {
        if (!value.Fields.TryGetValue(field, out var raw) || !raw.HasValue) return null;
        int divisor = field switch
        {
            MeasurementField.Speed or MeasurementField.AverageSpeed => 360,
            MeasurementField.Inclination or MeasurementField.RampAngle or MeasurementField.MetabolicEquivalent => 10,
            MeasurementField.PositiveElevation or MeasurementField.NegativeElevation when value.Kind == MeasurementKind.Treadmill => 10,
            MeasurementField.StrideCount when value.Kind == MeasurementKind.CrossTrainer => 10,
            MeasurementField.Resistance when value.Format.Resistance == ResistanceFormat.SInt16Tenths => 10,
            MeasurementField.StrokeRate or MeasurementField.AverageStrokeRate or MeasurementField.Cadence or MeasurementField.AverageCadence => 2,
            _ => 1
        };
        return (double)raw.Value / divisor;
    }
    public double? SpeedMetresPerSecond => GetValue(MeasurementField.Speed);
    public double? AverageSpeedMetresPerSecond => GetValue(MeasurementField.AverageSpeed);
    public double? DistanceMetres => GetValue(MeasurementField.Distance);
    public double? InclinationPercent => GetValue(MeasurementField.Inclination);
    public double? RampAngleDegrees => GetValue(MeasurementField.RampAngle);
    public double? PositiveElevationMetres => GetValue(MeasurementField.PositiveElevation);
    public double? NegativeElevationMetres => GetValue(MeasurementField.NegativeElevation);
    public double? InstantaneousPaceSecondsPer500Metres => GetValue(MeasurementField.InstantaneousPace);
    public double? AveragePaceSecondsPer500Metres => GetValue(MeasurementField.AveragePace);
    public double? EnergyKilocalories => GetValue(MeasurementField.TotalEnergy);
    public double? EnergyPerHourKilocalories => GetValue(MeasurementField.EnergyPerHour);
    public double? EnergyPerMinuteKilocalories => GetValue(MeasurementField.EnergyPerMinute);
    public double? HeartRateBeatsPerMinute => GetValue(MeasurementField.HeartRate);
    public double? MetabolicEquivalent => GetValue(MeasurementField.MetabolicEquivalent);
    public double? ElapsedTimeSeconds => GetValue(MeasurementField.ElapsedTime);
    public double? RemainingTimeSeconds => GetValue(MeasurementField.RemainingTime);
    public double? ForceOnBeltNewtons => GetValue(MeasurementField.ForceOnBelt);
    public double? PowerWatts => GetValue(MeasurementField.Power);
    public double? AveragePowerWatts => GetValue(MeasurementField.AveragePower);
    public double? StepRatePerMinute => GetValue(MeasurementField.StepRate);
    public double? AverageStepRatePerMinute => GetValue(MeasurementField.AverageStepRate);
    public double? StrideCount => GetValue(MeasurementField.StrideCount);
    public double? ResistanceLevel => GetValue(MeasurementField.Resistance);
    public double? FloorCount => GetValue(MeasurementField.FloorCount);
    public double? StepCount => GetValue(MeasurementField.StepCount);
    public double? StrokeRatePerMinute => GetValue(MeasurementField.StrokeRate);
    public double? StrokeCount => GetValue(MeasurementField.StrokeCount);
    public double? AverageStrokeRatePerMinute => GetValue(MeasurementField.AverageStrokeRate);
    public double? CadenceRpm => GetValue(MeasurementField.Cadence);
    public double? AverageCadenceRpm => GetValue(MeasurementField.AverageCadence);
}
