using System;
using System.Collections.Generic;

namespace DeanCochran.Ftms;

public enum RangeKind { Speed, Inclination, Resistance, HeartRate, Power }
public enum RangeUnit { KilometresPerHour, Percent, Level, BeatsPerMinute, Watts }
public enum ResistanceFormat { UInt8Whole, SInt16Tenths }
public enum RangeInspectionStatus { Valid, Length, Range }

/// <summary>Exact wire numerators and an explicit unit/scale, without rounding.</summary>
public sealed class SupportedRange
{
    public RangeKind Kind { get; }
    public int Minimum { get; }
    public int Maximum { get; }
    public int Increment { get; }
    public int ScaleDivisor { get; }
    public RangeUnit Unit { get; }
    public double MinimumValue => (double)Minimum / ScaleDivisor;
    public double MaximumValue => (double)Maximum / ScaleDivisor;
    public double IncrementValue => (double)Increment / ScaleDivisor;
    public SupportedRange(RangeKind kind, int minimum, int maximum, int increment, int scaleDivisor, RangeUnit unit)
    {
        Kind = kind; Minimum = minimum; Maximum = maximum; Increment = increment;
        ScaleDivisor = scaleDivisor; Unit = unit;
    }
}

public sealed class RangeInspectionCandidate
{
    public string Profile { get; }
    public int ExpectedLength { get; }
    public RangeInspectionStatus Status { get; }
    public SupportedRange? Value { get; }
    internal RangeInspectionCandidate(string profile, int length, RangeInspectionStatus status, SupportedRange? value)
    { Profile = profile; ExpectedLength = length; Status = status; Value = value; }
}

public sealed class RangeInspection
{
    public string SelectedProfile => selected.Profile;
    public int ActualLength { get; }
    public int ExpectedLength => selected.ExpectedLength;
    public RangeInspectionStatus Status => selected.Status;
    public SupportedRange? Value => selected.Value;
    public IReadOnlyList<RangeInspectionCandidate> Candidates { get; }
    private readonly RangeInspectionCandidate selected;
    internal RangeInspection(int actualLength, RangeInspectionCandidate selected, RangeInspectionCandidate[] candidates)
    { ActualLength = actualLength; this.selected = selected; Candidates = Array.AsReadOnly(candidates); }
}

public static class RangeCodec
{
    private static (string profile, int width, bool signed, int scale, RangeUnit unit) Layout(RangeKind kind, ResistanceFormat format)
    {
        Wire.Require(format == ResistanceFormat.UInt8Whole || format == ResistanceFormat.SInt16Tenths, FtmsError.Kind);
        Wire.Require(format == ResistanceFormat.UInt8Whole || kind == RangeKind.Resistance, FtmsError.Kind);
        return kind switch
        {
            RangeKind.Speed => ("uint16Hundredths", 2, false, 100, RangeUnit.KilometresPerHour),
            RangeKind.Inclination => ("signed16Tenths", 2, true, 10, RangeUnit.Percent),
            RangeKind.Resistance when format == ResistanceFormat.SInt16Tenths => ("signed16Tenths", 2, true, 10, RangeUnit.Level),
            RangeKind.Resistance => ("uint8Whole", 1, false, 1, RangeUnit.Level),
            RangeKind.HeartRate => ("uint8Bpm", 1, false, 1, RangeUnit.BeatsPerMinute),
            RangeKind.Power => ("signed16Watts", 2, true, 1, RangeUnit.Watts),
            _ => throw new FtmsException(FtmsError.Kind)
        };
    }

    public static SupportedRange Decode(RangeKind kind, ReadOnlySpan<byte> bytes, ResistanceFormat format = ResistanceFormat.UInt8Whole)
    {
        var l = Layout(kind, format);
        Wire.Require(bytes.Length == l.width * 3, FtmsError.Length);
        int min = Wire.Read(bytes, 0, l.width, l.signed), max = Wire.Read(bytes, l.width, l.width, l.signed);
        int inc = Wire.Read(bytes, l.width * 2, l.width);
        Wire.Require(min <= max && inc > 0);
        return new SupportedRange(kind, min, max, inc, l.scale, l.unit);
    }

    public static DecodeResult<SupportedRange> TryDecode(RangeKind kind, ReadOnlySpan<byte> bytes, ResistanceFormat format = ResistanceFormat.UInt8Whole)
    {
        try { return new DecodeResult<SupportedRange>(Decode(kind, bytes, format)); }
        catch (FtmsException e) { return new DecodeResult<SupportedRange>(e.Error); }
    }

    public static byte[] Encode(SupportedRange value, ResistanceFormat format = ResistanceFormat.UInt8Whole)
    {
        if (value == null) throw new ArgumentNullException(nameof(value));
        var l = Layout(value.Kind, format);
        Wire.Require(value.Minimum <= value.Maximum && value.Increment > 0 && value.ScaleDivisor == l.scale && value.Unit == l.unit);
        Wire.Bounds(value.Minimum, l.width, l.signed); Wire.Bounds(value.Maximum, l.width, l.signed); Wire.Bounds(value.Increment, l.width);
        var bytes = new byte[l.width * 3];
        Wire.Write(bytes, 0, value.Minimum, l.width); Wire.Write(bytes, l.width, value.Maximum, l.width); Wire.Write(bytes, l.width * 2, value.Increment, l.width);
        return bytes;
    }

    public static bool TryEncode(SupportedRange value, Span<byte> destination, out int written, ResistanceFormat format = ResistanceFormat.UInt8Whole) =>
        Wire.Copy(Encode(value, format), destination, out written);

    public static RangeInspection Inspect(RangeKind kind, ReadOnlySpan<byte> bytes, ResistanceFormat format = ResistanceFormat.UInt8Whole)
    {
        var selected = Layout(kind, format);
        var formats = kind == RangeKind.Resistance ? new[] { ResistanceFormat.UInt8Whole, ResistanceFormat.SInt16Tenths } : new[] { format };
        var candidates = new RangeInspectionCandidate[formats.Length];
        int index = 0;
        for (int i = 0; i < formats.Length; i++)
        {
            var l = Layout(kind, formats[i]);
            var result = TryDecode(kind, bytes, formats[i]);
            candidates[i] = new RangeInspectionCandidate(l.profile, l.width * 3,
                result.Success ? RangeInspectionStatus.Valid : result.Error == FtmsError.Length ? RangeInspectionStatus.Length : RangeInspectionStatus.Range, result.Value);
            if (l.profile == selected.profile) index = i;
        }
        return new RangeInspection(bytes.Length, candidates[index], candidates);
    }
}
