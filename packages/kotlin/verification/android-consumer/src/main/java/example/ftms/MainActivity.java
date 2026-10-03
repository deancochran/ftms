package example.ftms;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import io.github.deancochran.ftms.FeatureCodec;
import io.github.deancochran.ftms.measurement.MeasurementReader;
import io.github.deancochran.ftms.measurement.MeasurementDecodeResult;
import java.util.UUID;

/** Offline consumer only: no Bluetooth permissions or device controls. */
public final class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        long word = FeatureCodec.decode(new byte[] {-1, -1, -1, -1, 0, 0, 0, 0}).getMachine();
        if (word != 0xffffffffL) throw new AssertionError("unsigned feature mismatch");
        MeasurementDecodeResult result = MeasurementReader.decode(
            UUID.fromString("00002ad2-0000-1000-8000-00805f9b34fb"),
            new byte[] {0, 0, 0x10, 0x0e});
        if (!(result instanceof MeasurementDecodeResult.Decoded)
            || !Double.valueOf(10.0).equals(((MeasurementDecodeResult.Decoded) result).getMeasurement().getSpeedMps()))
            throw new AssertionError("universal measurement mismatch");
        TextView text = new TextView(this);
        text.setText("FTMS artifact decoded unsigned Feature word: " + word);
        setContentView(text);
    }
}
