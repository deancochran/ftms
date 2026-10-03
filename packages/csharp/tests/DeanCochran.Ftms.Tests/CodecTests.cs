using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.IO;
using System.Text.Json;
using Xunit;

namespace DeanCochran.Ftms.Tests;

public sealed class CodecTests
{
    [Fact]
    public void UuidDecoderReadsCanonicalAllFieldPacketsForEveryFamily()
    {
        var root = new DirectoryInfo(AppContext.BaseDirectory);
        while (root != null && !File.Exists(Path.Combine(root.FullName, "shared/conformance/measurements/v1/vectors.json"))) root = root.Parent;
        Assert.NotNull(root);
        using var corpus = JsonDocument.Parse(File.ReadAllText(Path.Combine(root!.FullName, "shared/conformance/measurements/v1/vectors.json")));
        int count = 0;
        foreach (var fixture in corpus.RootElement.GetProperty("cases").EnumerateArray())
        {
            string id = fixture.GetProperty("id").GetString()!;
            if (!id.StartsWith("equipment-", StringComparison.Ordinal) || !id.EndsWith("-all-fields", StringComparison.Ordinal)) continue;
            int kind = fixture.GetProperty("kind").GetInt32();
            byte[] bytes = fixture.GetProperty("bytes").EnumerateArray().Select(value => value.GetByte()).ToArray();
            string shortUuid = (0x2acd + kind).ToString("x4", CultureInfo.InvariantCulture);
            foreach (string uuid in new[] { shortUuid, "0000" + shortUuid + "-0000-1000-8000-00805f9b34fb" })
            {
                var result = MeasurementUuidCodec.Decode(uuid, bytes);
                Assert.Equal(MeasurementUuidDecodeStatus.Known, result.Status);
                Assert.Equal((MeasurementKind)kind, result.Kind);
                var expected = fixture.GetProperty("decoded");
                uint present = expected.GetProperty("present").GetUInt32();
                uint unavailable = expected.GetProperty("unavailable").GetUInt32();
                for (int index = 0; index < 30; index++)
                {
                    bool found = result.Measurement!.Fields.TryGetValue((MeasurementField)index, out int? value);
                    Assert.Equal((present & (1u << index)) != 0, found);
                    if (found) Assert.Equal((unavailable & (1u << index)) != 0 ? (int?)null : expected.GetProperty("values")[index].GetInt32(), value);
                }
                Assert.Equal(bytes, MeasurementCodec.Encode(result.Measurement!));
            }
            count++;
        }
        Assert.Equal(6, count);
        Assert.Equal(MeasurementUuidDecodeStatus.Unsupported, MeasurementUuidCodec.Decode("00002ad20000-1000800000805f9b34fb", Array.Empty<byte>()).Status);
    }

    [Fact]
    public void FeatureWordsKeepUnsignedAndUnknownBits()
    {
        var bytes = new byte[] { 255, 255, 255, 255, 0, 0, 0, 128 };
        var value = FeatureCodec.Decode(bytes);
        Assert.Equal(uint.MaxValue, value.MachineRaw);
        Assert.Equal(0x80000000u, value.TargetUnknown);
        Assert.Equal(bytes, FeatureCodec.Encode(value));
        Assert.Equal(FtmsError.Length, FeatureCodec.TryDecode(bytes.AsSpan(1)).Error);
        Assert.False(value.Target(32));
    }

    [Fact]
    public void BufferWritesAreAtomicOnCapacityAndInvalidInput()
    {
        byte[] destination = Enumerable.Repeat((byte)0xaa, 8).ToArray();
        Assert.False(FeatureCodec.TryEncode(new Features(1, 2), destination.AsSpan(0, 7), out int written));
        Assert.Equal(0, written);
        Assert.All(destination, value => Assert.Equal(0xaa, value));
        Assert.Throws<FtmsException>(() => ControlCodec.TryEncodeRequest(new ControlRequest(ControlOpcode.TargetSpeed, 65536), destination, out _));
        Assert.All(destination, value => Assert.Equal(0xaa, value));
        Assert.True(ControlCodec.TryEncodeRequest(new ControlRequest(ControlOpcode.TargetPower, -100), destination, out written));
        Assert.Equal(3, written);
        Assert.Equal(new byte[] { 5, 156, 255 }, destination.Take(3));
    }

    [Fact]
    public void RangeFormatsAndWireWidthsAreExplicit()
    {
        byte[] bytes = { 246, 255, 100, 0, 1, 0 };
        Assert.Equal(FtmsError.Length, RangeCodec.TryDecode(RangeKind.Resistance, bytes).Error);
        var range = RangeCodec.Decode(RangeKind.Resistance, bytes, ResistanceFormat.SInt16Tenths);
        Assert.Equal(-1, range.MinimumValue);
        Assert.Equal(bytes, RangeCodec.Encode(range, ResistanceFormat.SInt16Tenths));
        Assert.Throws<FtmsException>(() => RangeCodec.Encode(range));
        Assert.Throws<FtmsException>(() => RangeCodec.Encode(new SupportedRange(RangeKind.Power, -32769, 10, 1, 1, RangeUnit.Watts)));
        Assert.Throws<FtmsException>(() => RangeCodec.Decode(RangeKind.Speed, bytes, ResistanceFormat.SInt16Tenths));
        Assert.Equal(RangeInspectionStatus.Length, RangeCodec.Inspect(RangeKind.Resistance, bytes).Status);
        Assert.Equal(RangeInspectionStatus.Valid, RangeCodec.Inspect(RangeKind.Resistance, bytes).Candidates[1].Status);
    }

    [Fact]
    public void ControlOperandsAreCopiedAndValidated()
    {
        int[] operands = { -32768, 32767, 255, 0 };
        var value = new ControlRequest(ControlOpcode.IndoorBikeSimulation, operands);
        operands[0] = 0;
        Assert.Equal(-32768, value.Operands[0]);
        Assert.Throws<NotSupportedException>(() => ((IList<int>)value.Operands)[0] = 0);
        Assert.Equal(new byte[] { 17, 0, 128, 255, 127, 255, 0 }, ControlCodec.EncodeRequest(value));
        Assert.Equal(FtmsError.Range, ControlCodec.TryDecodeRequest(new byte[] { 8, 0 }).Error);
        Assert.Equal(FtmsError.Kind, ControlCodec.TryDecodeRequest(new byte[] { 255 }).Error);
        Assert.Throws<FtmsException>(() => ControlCodec.EncodeRequest(new ControlRequest(ControlOpcode.Reset, 1)));
        Assert.Equal(new byte[] { 4, 255 }, ControlCodec.EncodeRequest(new ControlRequest(ControlOpcode.TargetResistance, 255), ControlResistanceFormat.UInt8Tenths));
    }

    [Fact]
    public void ResponseUnknownAndUnexpectedEvidenceCannotBeCanonicalizedSilently()
    {
        byte[] bytes = { 128, 5, 1, 99 };
        var response = ControlCodec.DecodeResponse(bytes);
        bytes[3] = 0;
        Assert.True(response.UnexpectedParameters);
        Assert.Equal(new byte[] { 99 }, response.UnexpectedParameterBytes);
        response.UnexpectedParameterBytes[0] = 0;
        Assert.Equal(new byte[] { 99 }, response.UnexpectedParameterBytes);
        Assert.Throws<FtmsException>(() => ControlCodec.EncodeResponse(response));
        Assert.Equal(new byte[] { 128, 255, 2 }, ControlCodec.EncodeResponse(new ControlResponse(255, 2)));
        Assert.Throws<FtmsException>(() => ControlCodec.EncodeResponse(new ControlResponse(255, 1)));
        Assert.Equal(FtmsError.Length, ControlCodec.TryDecodeResponse(new byte[] { 128, 19, 1, 1 }).Error);
    }

    [Fact]
    public void MeasurementLiteralHasPhysicalUnitsAndImmutableRawFields()
    {
        var value = MeasurementCodec.Decode(MeasurementKind.IndoorBike, new byte[] { 0x44, 0, 0x10, 0x0e, 0xb4, 0, 0xfa, 0 });
        Assert.Equal(10, value.Normalized.SpeedMetresPerSecond);
        Assert.Equal(90, value.Normalized.CadenceRpm);
        Assert.Equal(250, value.Normalized.PowerWatts);
        Assert.Null(value.Normalized.HeartRateBeatsPerMinute);
        var fields = new Dictionary<MeasurementField, int?> { [MeasurementField.Speed] = 100 };
        var input = new Measurement(MeasurementKind.Treadmill, 0, fields);
        fields[MeasurementField.Speed] = 0;
        Assert.Equal(100, input.Fields[MeasurementField.Speed]);
        Assert.Throws<NotSupportedException>(() => ((IDictionary<MeasurementField, int?>)input.Fields)[MeasurementField.Speed] = 0);
        Assert.Equal(new byte[] { 0, 0, 100, 0 }, MeasurementCodec.Encode(input));
    }

    [Fact]
    public void SentinelsMissingFieldsAndTruncationRemainDistinct()
    {
        var bytes = new byte[] { 8, 0, 10, 0, 255, 127, 0, 0 };
        var value = MeasurementCodec.Decode(MeasurementKind.Treadmill, bytes);
        Assert.True(value.Fields.ContainsKey(MeasurementField.Inclination));
        Assert.Null(value.Fields[MeasurementField.Inclination]);
        Assert.False(value.Fields.ContainsKey(MeasurementField.HeartRate));
        Assert.Equal(bytes, MeasurementCodec.Encode(value));
        var partial = MeasurementCodec.Decode(MeasurementKind.Treadmill, bytes.AsSpan(0, 7));
        Assert.True(partial.Diagnostics.Truncated);
        Assert.Equal(6, partial.BytesRead);
        Assert.False(partial.Fields.ContainsKey(MeasurementField.RampAngle));
        Assert.Throws<FtmsException>(() => MeasurementCodec.Encode(partial));
        Assert.Throws<FtmsException>(() => MeasurementCodec.Encode(new Measurement(MeasurementKind.Treadmill, 0, new Dictionary<MeasurementField, int?>())));
        Assert.Throws<FtmsException>(() => MeasurementCodec.Encode(new Measurement(MeasurementKind.Treadmill, 0x8001, new Dictionary<MeasurementField, int?>())));
    }

    [Fact]
    public void ExplicitMeasurementFormatSurvivesRoundTrip()
    {
        var format = new MeasurementFormat(ResistanceFormat.SInt16Tenths);
        var bytes = new byte[] { 0x21, 0, 0xf6, 0xff };
        var value = MeasurementCodec.Decode(MeasurementKind.IndoorBike, bytes, format);
        Assert.True(value.MoreData);
        Assert.Equal(-1, value.Normalized.ResistanceLevel);
        Assert.Equal(bytes, MeasurementCodec.Encode(value));
        Assert.True(MeasurementCodec.Decode(MeasurementKind.IndoorBike, bytes).Diagnostics.TrailingBytes);
        Assert.Equal(FtmsError.Kind, MeasurementCodec.TryDecode((MeasurementKind)6, Array.Empty<byte>()).Error);
    }

    [Fact]
    public void UuidDispatchCoversAllFamiliesAndKeepsHonestEvidence()
    {
        var cases = new Dictionary<string, MeasurementKind>
        {
            ["2acd"] = MeasurementKind.Treadmill,
            ["0x2ace"] = MeasurementKind.CrossTrainer,
            ["2acf"] = MeasurementKind.StepClimber,
            ["2ad0"] = MeasurementKind.StairClimber,
            ["2ad1"] = MeasurementKind.Rower,
            ["00002ad2-0000-1000-8000-00805f9b34fb"] = MeasurementKind.IndoorBike,
        };
        foreach (var item in cases)
        {
            var result = MeasurementUuidCodec.Decode(item.Key, new byte[] { 0, 0 });
            Assert.Equal(MeasurementUuidDecodeStatus.Known, result.Status);
            Assert.Equal(item.Value, result.Kind);
            Assert.NotNull(result.Measurement);
        }
        var bike = MeasurementUuidCodec.Decode("2ad2", new byte[] { 0x44, 0, 0x10, 0x0e, 0xb4, 0, 0xfa, 0 });
        Assert.Equal(10, bike.Normalized!.SpeedMetresPerSecond);
        Assert.Equal(90, bike.Normalized.CadenceRpm);
        Assert.Equal(250, bike.Normalized.PowerWatts);
        var partial = MeasurementUuidCodec.Decode("2ad2", new byte[] { 0 });
        Assert.Equal(MeasurementUuidDecodeStatus.Known, partial.Status);
        Assert.True(partial.Diagnostics!.Truncated);
        Assert.Null(partial.Normalized!.SpeedMetresPerSecond);
        Assert.Equal(MeasurementUuidDecodeStatus.Unsupported, MeasurementUuidCodec.Decode("2ad3", Array.Empty<byte>()).Status);
        Assert.Equal(MeasurementUuidDecodeStatus.Unsupported, MeasurementUuidCodec.Decode("12342ad2-0000-1000-8000-00805f9b34fb", Array.Empty<byte>()).Status);
    }

    [Fact]
    public void LegacyPaceNeverClaimsSecondsPer500Metres()
    {
        var format = new MeasurementFormat(treadmillPace: TreadmillPaceFormat.UInt8Legacy);
        var result = MeasurementUuidCodec.Decode("2acd", new byte[] { 0x20, 0, 0, 0, 120 }, format);
        Assert.Equal(120, result.Measurement!.Fields[MeasurementField.InstantaneousPace]);
        Assert.Null(result.Normalized!.GetValue(MeasurementField.InstantaneousPace));
        Assert.Null(result.Normalized.InstantaneousPaceSecondsPer500Metres);
        Assert.Null(result.Normalized.AveragePaceSecondsPer500Metres);

        var signedResistance = MeasurementUuidCodec.Decode("2ad2", new byte[] { 0x21, 0, 0xf6, 0xff },
            new MeasurementFormat(ResistanceFormat.SInt16Tenths));
        Assert.Equal(-1, signedResistance.Normalized!.ResistanceLevel);

        var zero = MeasurementUuidCodec.Decode("2ad2", new byte[] { 0, 0, 0, 0 });
        Assert.Equal(0, zero.Normalized!.SpeedMetresPerSecond);
        var unavailable = MeasurementUuidCodec.Decode("2ad2", new byte[] { 0, 1, 0, 0, 255, 255, 255 });
        Assert.Null(unavailable.Normalized!.EnergyKilocalories);
    }

    [Fact]
    public void TrainingStatusRetainsInvalidUtf8AndRejectsInvalidUtf16()
    {
        byte[] bytes = { 1, 13, 0xff };
        var value = StatusCodec.DecodeTraining(bytes);
        bytes[2] = 0;
        Assert.Contains("invalid_utf8", value.Diagnostics.Issues);
        Assert.Equal(new byte[] { 0xff }, value.TextBytes);
        Assert.Throws<FtmsException>(() => StatusCodec.EncodeTraining(value));
        Assert.Throws<FtmsException>(() => new TrainingStatus(1, 13, "\ud800"));
        Assert.Throws<FtmsException>(() => StatusCodec.EncodeTraining(new TrainingStatus(0, 13, "unexpected")));
        Assert.Equal(new byte[] { 1, 13, 0xc3, 0xa9 }, StatusCodec.EncodeTraining(new TrainingStatus(1, 13, "é")));
    }

    [Fact]
    public void StatusActionsAndOperandProfilesAreValidated()
    {
        Assert.Throws<FtmsException>(() => StatusCodec.EncodeMachine(new MachineStatus(1, 1)));
        Assert.Throws<FtmsException>(() => StatusCodec.EncodeMachine(new MachineStatus(2, 0)));
        Assert.Throws<FtmsException>(() => StatusCodec.EncodeMachine(new MachineStatus(5, parameter: new ControlRequest(ControlOpcode.TargetPower, 10))));
        var value = StatusCodec.DecodeMachine(new byte[] { 7, 246, 255 });
        Assert.Equal(-10, value.Parameter!.Operands[0]);
        Assert.Equal(new byte[] { 7, 246, 255 }, StatusCodec.EncodeMachine(value));
        Assert.Contains("unknown_opcode", StatusCodec.DecodeMachine(new byte[] { 0x42, 7 }).Diagnostics.Issues);
        Assert.True(StatusCodec.DecodeMachine(new byte[] { 5, 0 }).Diagnostics.Truncated);
    }

    [Fact]
    public void DecodersDoNotLeakIndexExceptionsForDeterministicMalformedInput()
    {
        var random = new Random(23224);
        for (int length = 0; length < 65; length++)
        for (int sample = 0; sample < 32; sample++)
        {
            var bytes = new byte[length]; random.NextBytes(bytes);
            _ = FeatureCodec.TryDecode(bytes);
            _ = ControlCodec.TryDecodeRequest(bytes);
            _ = ControlCodec.TryDecodeResponse(bytes);
            _ = StatusCodec.DecodeTraining(bytes);
            _ = StatusCodec.DecodeMachine(bytes);
            foreach (var kind in Enum.GetValues<MeasurementKind>()) _ = MeasurementCodec.TryDecode(kind, bytes);
            foreach (var kind in Enum.GetValues<RangeKind>()) _ = RangeCodec.TryDecode(kind, bytes);
        }
    }

    [Fact]
    public void NormalizationIsCultureIndependent()
    {
        var previous = CultureInfo.CurrentCulture;
        try
        {
            CultureInfo.CurrentCulture = new CultureInfo("fr-FR");
            var value = MeasurementCodec.Decode(MeasurementKind.Treadmill, new byte[] { 0, 0, 104, 1 });
            Assert.Equal(1, value.Normalized.SpeedMetresPerSecond);
        }
        finally { CultureInfo.CurrentCulture = previous; }
    }
}
