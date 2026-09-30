package example;

import io.github.deancochran.ftms.FeatureCodec;
import io.github.deancochran.ftms.Features;
import java.util.Arrays;

public final class Consumer {
    public static void main(String[] args) {
        byte[] wire = new byte[] {-1, -1, -1, -1, 0, 0, 0, -128};
        Features features = FeatureCodec.decode(wire);
        if (features.getMachine() != 0xffffffffL || features.getTarget() != 0x80000000L)
            throw new AssertionError("unsigned/unknown Feature bits lost");
        if (!Arrays.equals(wire, FeatureCodec.encode(features)))
            throw new AssertionError("literal bytes differ");
        try {
            FeatureCodec.decode(new byte[7]);
            throw new AssertionError("truncated feature accepted");
        } catch (IllegalArgumentException expected) {
            // Protocol argument validation, not an array bounds exception.
        }
        System.out.println("Java isolated artifact consumer passed");
    }
}
