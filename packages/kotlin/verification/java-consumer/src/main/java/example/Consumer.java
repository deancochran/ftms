package example;

import io.github.deancochran.ftms.FeatureCodec;
import io.github.deancochran.ftms.Features;
import io.github.deancochran.ftms.measurement.MeasurementDecodeResult;
import io.github.deancochran.ftms.measurement.MeasurementReader;
import java.util.Arrays;
import java.util.UUID;

public final class Consumer {
    public static void main(String[] args) {
        byte[] wire = new byte[] {-1, -1, -1, -1, 0, 0, 0, -128};
        Features features = FeatureCodec.decode(wire);
        if (features.getMachine() != 0xffffffffL || features.getTarget() != 0x80000000L)
            throw new AssertionError("unsigned/unknown Feature bits lost");
        if (!Arrays.equals(wire, FeatureCodec.encode(features)))
            throw new AssertionError("literal bytes differ");
        MeasurementDecodeResult reading = MeasurementReader.decode(
            UUID.fromString("00002ad2-0000-1000-8000-00805f9b34fb"), new byte[] {0, 0, 16, 14});
        if (!(reading instanceof MeasurementDecodeResult.Decoded decoded) ||
            decoded.getMeasurement().getSpeedMps() != 10.0)
            throw new AssertionError("normalized measurement missing");
        try {
            FeatureCodec.decode(new byte[7]);
            throw new AssertionError("truncated feature accepted");
        } catch (IllegalArgumentException expected) {
            // Protocol argument validation, not an array bounds exception.
        }
        System.out.println("Java isolated artifact consumer passed");
    }
}
