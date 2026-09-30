package example.ftms;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import io.github.deancochran.ftms.FeatureCodec;

/** Offline consumer only: no Bluetooth permissions or device controls. */
public final class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        long word = FeatureCodec.decode(new byte[] {-1, -1, -1, -1, 0, 0, 0, 0}).getMachine();
        if (word != 0xffffffffL) throw new AssertionError("unsigned feature mismatch");
        TextView text = new TextView(this);
        text.setText("FTMS artifact decoded unsigned Feature word: " + word);
        setContentView(text);
    }
}
