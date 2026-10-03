using System;
using DeanCochran.Ftms;

public static class Consumer
{
    public static void Verify()
    {
        var features = FeatureCodec.Decode(FeatureCodec.Encode(new Features(1, 2)));
        if (features.TargetRaw != 2) throw new Exception("Feature codec failed.");
        var measurement = MeasurementCodec.Decode(MeasurementKind.IndoorBike,
            new byte[] { 0x44, 0, 0x10, 0x0e, 0xb4, 0, 0xfa, 0 });
        if (measurement.Normalized.SpeedMetresPerSecond != 10 || measurement.Normalized.CadenceRpm != 90 || measurement.Normalized.PowerWatts != 250)
            throw new Exception("Measurement codec failed.");
        var universal = MeasurementUuidCodec.Decode("0x2ad2", new byte[] { 0x44, 0, 0x10, 0x0e, 0xb4, 0, 0xfa, 0 });
        if (universal.Status != MeasurementUuidDecodeStatus.Known || universal.Normalized!.SpeedMetresPerSecond != 10)
            throw new Exception("UUID measurement codec failed.");
        if (ControlCodec.EncodeRequest(new ControlRequest(ControlOpcode.TargetPower, 250))[1] != 250)
            throw new Exception("Control codec failed.");
        if (ControlCodec.TryDecodeResponse(new byte[] { 128 }).Success)
            throw new Exception("Malformed response accepted.");
        var report = CapabilityEvaluator.Evaluate(new CapabilitySnapshot(2, 1, 1,
            new[] { new CapabilityCharacteristic("00002acc00001000800000805f9b34fb", 2, 1, 0, new byte[8]) }, new CapabilityC7(false, false)));
        if (report.Operations.Count != 21) throw new Exception("Capability report failed.");
        Console.WriteLine("Installed FTMS consumer passed.");
    }
    public static void Main() => Verify();
}
