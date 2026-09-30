package io.github.deancochran.ftms
import kotlin.test.*
class FtmsTest {
 @Test fun literalFeatureAndRangeBytes() { assertContentEquals(byteArrayOf(-1,-1,-1,-1,-1,-1,-1,-1),FeatureCodec.encode(Features(0xffffffffL,0xffffffffL))); val r=SupportedRange(RangeKind.POWER,-100,4000,5,1,RangeUnit.WATTS);assertContentEquals(byteArrayOf(156.toByte(),255.toByte(),160.toByte(),15,5,0),RangeCodec.encode(r));assertEquals(-100,RangeCodec.decode(RangeKind.POWER,byteArrayOf(156.toByte(),255.toByte(),160.toByte(),15,5,0)).minimum) }
 @Test fun inspectionPreservesAlternateProvenance() { val i=RangeCodec.inspect(RangeKind.RESISTANCE,byteArrayOf(0,0,100,0,1,0));assertEquals(InspectionStatus.LENGTH,i.status);assertEquals(RangeProfile.UINT8_WHOLE,i.selectedProfile);assertEquals(InspectionStatus.VALID,i.candidates[1].status);assertEquals(10,i.candidates[1].value!!.scaleDivisor) }
 @Test fun controlsAreTypedAndDefensive() { val decoded=ControlCodec.decodeRequest(byteArrayOf(3,133.toByte(),255.toByte()));assertContentEquals(longArrayOf(-123),decoded.operands());assertContentEquals(byteArrayOf(3,133.toByte(),255.toByte()),ControlCodec.encodeRequest(decoded)); val r=ControlCodec.decodeResponse(byteArrayOf(128.toByte(),19,1,1,0,2,0));assertEquals(1,r.parameter);assertContentEquals(byteArrayOf(128.toByte(),19,1,1,0,2,0),ControlCodec.encodeResponse(r)) }
}
