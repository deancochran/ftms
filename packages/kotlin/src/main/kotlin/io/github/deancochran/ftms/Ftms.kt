@file:JvmName("Ftms")
package io.github.deancochran.ftms

/** Pure JVM FTMS wire codecs. Inputs and outputs are copied at the public boundary. */
public enum class FtmsError { LENGTH, KIND, RANGE }
public class FtmsException(public val error: FtmsError, message: String = error.name) : IllegalArgumentException(message)
private fun error(e: FtmsError): Nothing = throw FtmsException(e)
private fun ByteArray.u(i: Int) = this[i].toInt() and 255
private fun ByteArray.u16(i: Int) = u(i) or (u(i + 1) shl 8)
private fun ByteArray.s16(i: Int) = u16(i).let { if (it < 32768) it else it - 65536 }
private fun u16(v: Long): ByteArray = byteArrayOf(v.toByte(), (v ushr 8).toByte())
private fun valid(v: Long, low: Long, high: Long) { if (v !in low..high) error(FtmsError.RANGE) }

public class Features(machine: Long, target: Long) {
  public val machine: Long = machine; public val target: Long = target
  init { valid(machine, 0, 0xffffffffL); valid(target, 0, 0xffffffffL) }
}
public object FeatureCodec {
  @JvmStatic public fun decode(bytes: ByteArray): Features {
    if(bytes.size != 8) error(FtmsError.LENGTH)
    fun word(i:Int): Long = bytes.u(i).toLong() or (bytes.u(i+1).toLong() shl 8) or (bytes.u(i+2).toLong() shl 16) or (bytes.u(i+3).toLong() shl 24)
    return Features(word(0),word(4))
  }
  @JvmStatic public fun encode(value: Features): ByteArray = ByteArray(8) { i -> (((if(i < 4) value.machine else value.target) ushr ((i % 4) * 8)) and 255).toByte() }
}

public enum class RangeKind { SPEED, INCLINATION, RESISTANCE, HEART_RATE, POWER }
public enum class RangeUnit(public val wire: Int) { KILOMETRES_PER_HOUR(0), PERCENT(1), LEVEL(2), BEATS_PER_MINUTE(3), WATTS(4) }
public enum class ResistanceRangeFormat { UINT8_WHOLE, SINT16_TENTHS }
public enum class RangeProfile { UINT16_HUNDREDTHS, SINT16_TENTHS, UINT8_WHOLE, UINT8_BPM, SINT16_WATTS }
public enum class InspectionStatus { VALID, LENGTH, RANGE }
public class SupportedRange(public val kind: RangeKind, public val minimum: Int, public val maximum: Int, public val increment: Int, public val scaleDivisor: Int, public val unit: RangeUnit)
public class RangeCandidate(public val profile: RangeProfile, public val expectedLength: Int, public val status: InspectionStatus, value: SupportedRange?) { public val value: SupportedRange? = value?.let { SupportedRange(it.kind,it.minimum,it.maximum,it.increment,it.scaleDivisor,it.unit) } }
public class RangeInspection(public val selectedProfile: RangeProfile, public val actualLength: Int, public val expectedLength: Int, public val status: InspectionStatus, value: SupportedRange?, candidates: List<RangeCandidate>) { public val value: SupportedRange? = value?.let { SupportedRange(it.kind,it.minimum,it.maximum,it.increment,it.scaleDivisor,it.unit) }; public val candidates: List<RangeCandidate> = java.util.Collections.unmodifiableList(candidates.toList()) }
public object RangeCodec {
  private fun profile(k:RangeKind, f:ResistanceRangeFormat) = when(k) { RangeKind.SPEED->RangeProfile.UINT16_HUNDREDTHS; RangeKind.INCLINATION->RangeProfile.SINT16_TENTHS; RangeKind.RESISTANCE->if(f==ResistanceRangeFormat.SINT16_TENTHS) RangeProfile.SINT16_TENTHS else RangeProfile.UINT8_WHOLE; RangeKind.HEART_RATE->RangeProfile.UINT8_BPM; RangeKind.POWER->RangeProfile.SINT16_WATTS }
  private fun metadata(k:RangeKind,f:ResistanceRangeFormat)=when(k) { RangeKind.SPEED->100 to RangeUnit.KILOMETRES_PER_HOUR; RangeKind.INCLINATION->10 to RangeUnit.PERCENT; RangeKind.RESISTANCE->if(f==ResistanceRangeFormat.SINT16_TENTHS)10 to RangeUnit.LEVEL else 1 to RangeUnit.LEVEL; RangeKind.HEART_RATE->1 to RangeUnit.BEATS_PER_MINUTE; RangeKind.POWER->1 to RangeUnit.WATTS }
  private fun length(p:RangeProfile)=if(p==RangeProfile.UINT8_WHOLE || p==RangeProfile.UINT8_BPM)3 else 6
  @JvmStatic @JvmOverloads public fun decode(kind:RangeKind, bytes:ByteArray, format:ResistanceRangeFormat=ResistanceRangeFormat.UINT8_WHOLE):SupportedRange {
    if(format==ResistanceRangeFormat.SINT16_TENTHS && kind != RangeKind.RESISTANCE) error(FtmsError.KIND)
    val p=profile(kind,format); if(bytes.size != length(p)) error(FtmsError.LENGTH)
    val signed=p==RangeProfile.SINT16_TENTHS || p==RangeProfile.SINT16_WATTS
    val min=if(bytes.size==3) bytes.u(0) else if(signed) bytes.s16(0) else bytes.u16(0)
    val max=if(bytes.size==3) bytes.u(1) else if(signed) bytes.s16(2) else bytes.u16(2)
    val inc=if(bytes.size==3) bytes.u(2) else bytes.u16(4)
    if(min>max || inc==0) error(FtmsError.RANGE); val (d,u)=metadata(kind,format); return SupportedRange(kind,min,max,inc,d,u)
  }
  @JvmStatic @JvmOverloads public fun encode(v:SupportedRange, format:ResistanceRangeFormat=ResistanceRangeFormat.UINT8_WHOLE):ByteArray {
    if(format==ResistanceRangeFormat.SINT16_TENTHS && v.kind != RangeKind.RESISTANCE) error(FtmsError.KIND)
    val (d,u)=metadata(v.kind,format); if(v.scaleDivisor!=d || v.unit!=u || v.minimum>v.maximum || v.increment<=0) error(FtmsError.RANGE)
    val p=profile(v.kind,format); val signed=p==RangeProfile.SINT16_TENTHS||p==RangeProfile.SINT16_WATTS; val max=if(length(p)==3)255 else 65535
    valid(v.increment.toLong(),1,max.toLong()); if(signed){valid(v.minimum.toLong(),-32768,32767);valid(v.maximum.toLong(),-32768,32767)}else{valid(v.minimum.toLong(),0,max.toLong());valid(v.maximum.toLong(),0,max.toLong())}
    return if(length(p)==3) byteArrayOf(v.minimum.toByte(),v.maximum.toByte(),v.increment.toByte()) else u16(v.minimum.toLong())+u16(v.maximum.toLong())+u16(v.increment.toLong())
  }
  @JvmStatic @JvmOverloads public fun inspect(kind:RangeKind, bytes:ByteArray, format:ResistanceRangeFormat=ResistanceRangeFormat.UINT8_WHOLE):RangeInspection {
    if(format==ResistanceRangeFormat.SINT16_TENTHS && kind!=RangeKind.RESISTANCE) error(FtmsError.KIND)
    val formats=if(kind==RangeKind.RESISTANCE) listOf(ResistanceRangeFormat.UINT8_WHOLE,ResistanceRangeFormat.SINT16_TENTHS) else listOf(format)
    val cs=formats.map { f -> val p=profile(kind,f); try { RangeCandidate(p,length(p),InspectionStatus.VALID,decode(kind,bytes,f)) } catch(e:FtmsException) { RangeCandidate(p,length(p),if(e.error==FtmsError.RANGE) InspectionStatus.RANGE else InspectionStatus.LENGTH,null) } }
    val selected=cs.first { it.profile==profile(kind,format) }; return RangeInspection(selected.profile,bytes.size,selected.expectedLength,selected.status,selected.value,cs)
  }
}

public enum class ResistanceControlFormat { SINT16_TENTHS, UINT8_TENTHS }
/** Typed raw FTMS operands in the exact wire order; values are signed only where the opcode specifies it. */
public class ControlRequest(opcode:Int, operands:LongArray) { public val opcode: Int = opcode; private val values=operands.copyOf(); init { valid(opcode.toLong(),0,20) }; public fun operands():LongArray=values.copyOf() }
public class ControlResponse(public val requestOpcode:Int,public val resultCode:Int,public val parameter:Int,public val low:Int,public val high:Int,public val unknownRequest:Int,public val unknownResult:Int,public val unexpectedParameters:Int)
public object ControlCodec {
  /** Decodes to a semantic command; all numeric fields retain their documented wire units. */
  @JvmStatic @JvmOverloads public fun decodeCommand(bytes: ByteArray, format: ResistanceControlFormat = ResistanceControlFormat.SINT16_TENTHS): ControlCommand = decodeRequest(bytes, format).typed()
  /** Encodes a semantic command using the same width and profile checks as raw requests. */
  @JvmStatic @JvmOverloads public fun encodeCommand(command: ControlCommand, format: ResistanceControlFormat = ResistanceControlFormat.SINT16_TENTHS): ByteArray = encodeRequest(command.raw, format)
  private val counts=intArrayOf(0,0,1,1,1,1,1,0,1,1,1,1,1,1,2,3,5,4,1,1,1)
  private fun n(op:Int,f:ResistanceControlFormat)=when(op){0,1,7->1;6,8,19->2;12->4;14->5;15,17->7;16->11;4->if(f==ResistanceControlFormat.UINT8_TENTHS)2 else 3;else->3}
  private fun bounds(op:Int,i:Int,f:ResistanceControlFormat):Pair<Long,Long> = when(op){3,5->-32768L to 32767L;4->if(f==ResistanceControlFormat.UINT8_TENTHS)0L to 255L else -32768L to 32767L;6,8,19->0L to 255L;12->0L to 0xffffffL;17->when(i){0,1->-32768L to 32767L;else->0L to 255L};else->0L to 65535L}
  @JvmStatic @JvmOverloads public fun decodeRequest(bytes:ByteArray, format:ResistanceControlFormat=ResistanceControlFormat.SINT16_TENTHS):ControlRequest { if(bytes.isEmpty())error(FtmsError.LENGTH); val op=bytes.u(0);if(op>20)error(FtmsError.KIND);if(bytes.size!=n(op,format))error(FtmsError.LENGTH); val a=LongArray(counts[op]); var at=1; for(i in a.indices){a[i]=when(op){3,5->bytes.s16(at).toLong();4->if(format==ResistanceControlFormat.UINT8_TENTHS)bytes.u(at).toLong() else bytes.s16(at).toLong();6,8,19->bytes.u(at).toLong();12->(bytes.u(at)or(bytes.u(at+1)shl 8)or(bytes.u(at+2)shl 16)).toLong();17->if(i<2)bytes.s16(at).toLong()else bytes.u(at).toLong();else->bytes.u16(at).toLong()};at+=if(op==12)3 else if(op in listOf(6,8,19)||op==4&&format==ResistanceControlFormat.UINT8_TENTHS||op==17&&i>=2)1 else 2}; if((op==8||op==19)&&a[0] !in 1L..2L)error(FtmsError.RANGE); return ControlRequest(op,a) }
  @JvmStatic @JvmOverloads public fun encodeRequest(v:ControlRequest, format:ResistanceControlFormat=ResistanceControlFormat.SINT16_TENTHS):ByteArray { val a=v.operands();if(a.size!=counts[v.opcode])error(FtmsError.LENGTH); if((v.opcode==8||v.opcode==19)&&a[0] !in 1L..2L)error(FtmsError.RANGE);a.forEachIndexed{i,x->val(b,t)=bounds(v.opcode,i,format);valid(x,b,t)}; val out=ByteArray(n(v.opcode,format));out[0]=v.opcode.toByte();var at=1;for(i in a.indices){val x=a[i];when{v.opcode==12->{out[at++]=x.toByte();out[at++]=(x ushr 8).toByte();out[at++]=(x ushr 16).toByte()};v.opcode in listOf(6,8,19)||v.opcode==4&&format==ResistanceControlFormat.UINT8_TENTHS||v.opcode==17&&i>=2->out[at++]=x.toByte();else->{out[at++]=x.toByte();out[at++]=(x ushr 8).toByte()}}};return out }
  @JvmStatic public fun decodeResponse(bytes:ByteArray):ControlResponse { if(bytes.size<3)error(FtmsError.LENGTH);if(bytes.u(0)!=128)error(FtmsError.KIND);val op=bytes.u(1);val result=bytes.u(2);if(op==19&&result==1&&bytes.size !in listOf(3,7))error(FtmsError.LENGTH);val spin=op==19&&result==1&&bytes.size==7;return ControlResponse(op,result,if(spin)1 else 0,if(spin)bytes.u16(3)else 0,if(spin)bytes.u16(5)else 0,if(op>20)1 else 0,if(result !in 1..5)1 else 0,if(!spin&&bytes.size>3)1 else 0) }
  @JvmStatic public fun encodeResponse(v:ControlResponse):ByteArray { valid(v.requestOpcode.toLong(),0,255);valid(v.resultCode.toLong(),1,5);valid(v.parameter.toLong(),0,1);valid(v.low.toLong(),0,65535);valid(v.high.toLong(),0,65535);valid(v.unknownRequest.toLong(),0,1);valid(v.unknownResult.toLong(),0,1);valid(v.unexpectedParameters.toLong(),0,1);if(v.unknownResult!=0||v.unexpectedParameters!=0||v.unknownRequest != if(v.requestOpcode>20)1 else 0)error(FtmsError.RANGE);if(v.requestOpcode>20&&v.resultCode!=2)error(FtmsError.KIND);if(v.parameter==1&&(v.requestOpcode!=19||v.resultCode!=1))error(FtmsError.RANGE);if(v.parameter==0&&(v.low!=0||v.high!=0))error(FtmsError.RANGE);return if(v.parameter==1)byteArrayOf(128.toByte(),v.requestOpcode.toByte(),v.resultCode.toByte())+u16(v.low.toLong())+u16(v.high.toLong())else byteArrayOf(128.toByte(),v.requestOpcode.toByte(),v.resultCode.toByte()) }
}

public enum class StopPauseAction(public val wire: Int) { STOP(1), PAUSE(2) }
public enum class SpinDownAction(public val wire: Int) { START(1), IGNORE(2) }

/**
 * The 21 FTMS procedures, with named operands instead of positional arrays.
 * Integer values are raw numerators, not floating-point human-unit conversions.
 * Encoding validates wire widths; a command is not permission to operate equipment.
 */
public sealed class ControlCommand protected constructor(public val raw: ControlRequest) {
  public data object RequestControl : ControlCommand(request(0))
  public data object Reset : ControlCommand(request(1))
  /** Speed in 0.01 km/h. */
  public data class TargetSpeed(public val hundredthsKmh: Int) : ControlCommand(request(2, hundredthsKmh))
  /** Inclination in 0.1 percent, signed. */
  public data class TargetInclination(public val tenthsPercent: Int) : ControlCommand(request(3, tenthsPercent))
  /** Resistance in 0.1 level; signed by default, unsigned byte only with the explicit profile. */
  public data class TargetResistance(public val tenthsLevel: Int) : ControlCommand(request(4, tenthsLevel))
  public data class TargetPower(public val watts: Int) : ControlCommand(request(5, watts))
  public data class TargetHeartRate(public val beatsPerMinute: Int) : ControlCommand(request(6, beatsPerMinute))
  public data object StartResume : ControlCommand(request(7))
  public data class StopPause(public val action: StopPauseAction) : ControlCommand(request(8, action.wire))
  public data class TargetEnergy(public val kilocalories: Int) : ControlCommand(request(9, kilocalories))
  public data class TargetSteps(public val steps: Int) : ControlCommand(request(10, steps))
  public data class TargetStrides(public val strides: Int) : ControlCommand(request(11, strides))
  public data class TargetDistance(public val metres: Int) : ControlCommand(request(12, metres))
  public data class TargetTrainingTime(public val seconds: Int) : ControlCommand(request(13, seconds))
  public data class TwoZoneTime(public val zone1Seconds: Int, public val zone2Seconds: Int) : ControlCommand(request(14, zone1Seconds, zone2Seconds))
  public data class ThreeZoneTime(public val zone1Seconds: Int, public val zone2Seconds: Int, public val zone3Seconds: Int) : ControlCommand(request(15, zone1Seconds, zone2Seconds, zone3Seconds))
  public data class FiveZoneTime(public val zone1Seconds: Int, public val zone2Seconds: Int, public val zone3Seconds: Int, public val zone4Seconds: Int, public val zone5Seconds: Int) : ControlCommand(request(16, zone1Seconds, zone2Seconds, zone3Seconds, zone4Seconds, zone5Seconds))
  /** Wind 0.001 m/s, grade 0.01 percent, rolling coefficient 0.0001, wind coefficient 0.01. */
  public data class IndoorBikeSimulation(public val windThousandthsMetresPerSecond: Int, public val gradeHundredthsPercent: Int, public val rollingResistanceTenThousandths: Int, public val windResistanceHundredths: Int) : ControlCommand(request(17, windThousandthsMetresPerSecond, gradeHundredthsPercent, rollingResistanceTenThousandths, windResistanceHundredths))
  public data class WheelCircumference(public val tenthsMillimetres: Int) : ControlCommand(request(18, tenthsMillimetres))
  public data class SpinDown(public val action: SpinDownAction) : ControlCommand(request(19, action.wire))
  public data class TargetCadence(public val halfRevolutionsPerMinute: Int) : ControlCommand(request(20, halfRevolutionsPerMinute))
}

private fun request(opcode: Int, vararg values: Int): ControlRequest = ControlRequest(opcode, values.map { it.toLong() }.toLongArray())

/** Called only after the raw decoder has validated opcode, operand count and action values. */
private fun ControlRequest.typed(): ControlCommand {
  val a = operands().map { it.toInt() }
  return when (opcode) {
    0 -> ControlCommand.RequestControl
    1 -> ControlCommand.Reset
    2 -> ControlCommand.TargetSpeed(a[0])
    3 -> ControlCommand.TargetInclination(a[0])
    4 -> ControlCommand.TargetResistance(a[0])
    5 -> ControlCommand.TargetPower(a[0])
    6 -> ControlCommand.TargetHeartRate(a[0])
    7 -> ControlCommand.StartResume
    8 -> ControlCommand.StopPause(StopPauseAction.entries.single { it.wire == a[0] })
    9 -> ControlCommand.TargetEnergy(a[0])
    10 -> ControlCommand.TargetSteps(a[0])
    11 -> ControlCommand.TargetStrides(a[0])
    12 -> ControlCommand.TargetDistance(a[0])
    13 -> ControlCommand.TargetTrainingTime(a[0])
    14 -> ControlCommand.TwoZoneTime(a[0], a[1])
    15 -> ControlCommand.ThreeZoneTime(a[0], a[1], a[2])
    16 -> ControlCommand.FiveZoneTime(a[0], a[1], a[2], a[3], a[4])
    17 -> ControlCommand.IndoorBikeSimulation(a[0], a[1], a[2], a[3])
    18 -> ControlCommand.WheelCircumference(a[0])
    19 -> ControlCommand.SpinDown(SpinDownAction.entries.single { it.wire == a[0] })
    20 -> ControlCommand.TargetCadence(a[0])
    else -> error(FtmsError.KIND)
  }
}
