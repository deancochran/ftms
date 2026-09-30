package io.github.deancochran.ftms;
import static org.junit.jupiter.api.Assertions.*; import org.junit.jupiter.api.Test;
public class JavaConsumerTest {
  @Test void consumesPublicApi() {
    Features feature = FeatureCodec.decode(new byte[]{1,0,0,0,0,0,0,0});
    assertEquals(1L, feature.getMachine());
    ControlRequest request = ControlCodec.decodeRequest(new byte[]{2,1,0});
    assertArrayEquals(new long[]{1L}, request.operands());
    ControlCommand.TargetPower power = new ControlCommand.TargetPower(250);
    assertArrayEquals(new byte[]{5, (byte)250, 0}, ControlCodec.encodeCommand(power));
    assertEquals(power, ControlCodec.decodeCommand(new byte[]{5, (byte)250, 0}));
    assertArrayEquals(new byte[]{7}, ControlCodec.encodeCommand(ControlCommand.StartResume.INSTANCE));
    assertArrayEquals(new byte[]{8, 2}, ControlCodec.encodeCommand(new ControlCommand.StopPause(StopPauseAction.PAUSE)));
    RangeInspection inspection = RangeCodec.inspect(RangeKind.RESISTANCE, new byte[]{1,100,1});
    assertEquals(InspectionStatus.VALID, inspection.getStatus());
    assertEquals(2, inspection.getCandidates().size());
    assertThrows(UnsupportedOperationException.class, () -> inspection.getCandidates().clear());
  }
}
