package io.github.deancochran.ftms.capability

import java.util.Collections

/** State of the caller-owned characteristic discovery attempt. */
public enum class DiscoveryState { NOT_ATTEMPTED, PARTIAL, COMPLETE, FAILED }
/** Scope of the selected FTMS service instance. */
public enum class ServiceScope { UNKNOWN, PRESENT, ABSENT, AMBIGUOUS }
/** Result of a caller-owned characteristic read. */
public enum class ReadState { NOT_ATTEMPTED, SUCCESS, FAILED }
/** Normalized reason for a failed read. */
public enum class ReadReason { NONE, GENERIC, SECURITY_REQUIRED, UNAVAILABLE, TIMEOUT, DISCONNECTED }
public enum class TruthValue { UNKNOWN, FALSE, TRUE }
public enum class Presence { UNKNOWN, ABSENT, UNIQUE, AMBIGUOUS }
public enum class DecodeState { NOT_ATTEMPTED, VALID, MALFORMED, FAILED }
public enum class Declaration { UNKNOWN, NOT_SUPPORTED, SUPPORTED }
/** Satisfied means static protocol prerequisites only, never execution authority. */
public enum class Prerequisite { NOT_APPLICABLE, SATISFIED, INCOMPLETE, INCONSISTENT }

/** Known FTMS characteristic kinds.  [UNKNOWN] is reserved for opaque UUIDs. */
public enum class KnownCharacteristicKind {
    UNKNOWN, FEATURE, TREADMILL_DATA, CROSS_TRAINER_DATA, STEP_CLIMBER_DATA,
    STAIR_CLIMBER_DATA, ROWER_DATA, INDOOR_BIKE_DATA, TRAINING_STATUS,
    SPEED_RANGE, INCLINATION_RANGE, RESISTANCE_RANGE, HEART_RATE_RANGE,
    POWER_RANGE, CONTROL_POINT, MACHINE_STATUS
}

public enum class RangeKind { SPEED, INCLINATION, RESISTANCE, HEART_RATE, POWER }
public enum class ResistanceRangeFormat { UINT8_WHOLE, SINT16_TENTHS }

/** Explicit caller-selected layout.  It never attempts to infer device format. */
public class RangeFormatOptions public constructor(
    public val resistanceRangeFormat: ResistanceRangeFormat = ResistanceRangeFormat.UINT8_WHOLE
)

public class C7Evidence public constructor(
    public val bondingSupported: TruthValue = TruthValue.UNKNOWN,
    public val featureMayChangeOverLifetime: TruthValue = TruthValue.UNKNOWN
)

/** Immutable observation input. UUID is canonical 32-character display/network-order hex. */
public class CharacteristicEvidence public constructor(
    public val uuid: String,
    public val properties: Int,
    public val readState: ReadState,
    public val readReason: ReadReason = ReadReason.NONE,
    readBytes: ByteArray = ByteArray(0)
) {
    private val bytes: ByteArray = readBytes.copyOf()
    public fun readBytes(): ByteArray = bytes.copyOf()
    // Kotlin internal members are callable from Java through their mangled JVM names.
    internal fun bytesInternal(): ByteArray = bytes.copyOf()
}

/** Immutable, caller-owned static evidence snapshot.  No I/O is performed by this package. */
public class CapabilitySnapshot public constructor(
    public val discovery: DiscoveryState,
    public val scope: ServiceScope,
    public val generation: Long,
    characteristics: List<CharacteristicEvidence>,
    public val c7: C7Evidence? = null
) {
    public val characteristics: List<CharacteristicEvidence> = immutableCopy(characteristics)
}

public class RangeValue public constructor(
    public val kind: RangeKind, public val minimum: Int, public val maximum: Int,
    public val increment: Int, public val scaleDivisor: Int, public val unit: String
)
public class FeatureEvidence internal constructor(
    public val presence: Presence, public val decode: DecodeState, public val inputIndex: Int?,
    public val machineRaw: Long, public val targetRaw: Long,
    public val machineUnknown: Long, public val targetUnknown: Long
)
public class RangeEvidence internal constructor(
    public val presence: Presence, public val decode: DecodeState, public val inputIndex: Int?,
    public val value: RangeValue?
)
public class OperationEvidence internal constructor(
    public val opcode: Int, public val targetBit: Int?, public val optionalInTable: Boolean,
    public val declaration: Declaration, public val prerequisite: Prerequisite, public val reasons: Int
)
public class Observation internal constructor(
    public val inputIndex: Int, public val uuid: String, public val properties: Int,
    public val knownKind: KnownCharacteristicKind, public val readState: ReadState,
    public val readReason: ReadReason, public val readSize: Int
)
public enum class DiagnosticCode {
    SCOPE_UNAVAILABLE, DISCOVERY_INCOMPLETE, DISCOVERY_FAILED, DUPLICATE_CHARACTERISTIC,
    REQUIRED_CHARACTERISTIC_MISSING, REQUIRED_PROPERTY_MISSING, EXCLUDED_PROPERTY_PRESENT,
    READ_FAILED, READ_SECURITY_REQUIRED, MALFORMED_BYTES, REQUIRED_RANGE_MISSING,
    SCOPE_CONTRADICTION, C7_EVIDENCE_INSUFFICIENT
}
public class CapabilityDiagnostic internal constructor(
    public val code: DiagnosticCode, public val knownKind: KnownCharacteristicKind, public val inputIndex: Int?
)
/** Complete ordered static report. It intentionally has no canExecute field. */
public class CapabilityReport internal constructor(
    public val generation: Long, public val discovery: DiscoveryState, public val scope: ServiceScope,
    public val observationCount: Int, public val diagnosticCount: Int,
    presence: List<Presence>, public val feature: FeatureEvidence, ranges: List<RangeEvidence>,
    operations: List<OperationEvidence>, observations: List<Observation>, diagnostics: List<CapabilityDiagnostic>
) {
    public val presence: List<Presence> = immutableCopy(presence)
    public val ranges: List<RangeEvidence> = immutableCopy(ranges)
    public val operations: List<OperationEvidence> = immutableCopy(operations)
    public val observations: List<Observation> = immutableCopy(observations)
    public val diagnostics: List<CapabilityDiagnostic> = immutableCopy(diagnostics)
}

/** Pure Kotlin/JVM evaluator for the shared FTMS static-capability contract. */
public object FtmsCapabilityEvaluator {
    private const val READ = 0x0002; private const val WRITE = 0x0008
    private const val NOTIFY = 0x0010; private const val INDICATE = 0x0020
    private val targetForOpcode: IntArray = intArrayOf(255,255,0,1,2,3,4,255,255,5,6,7,8,9,10,11,12,13,14,15,16)
    private val rangeForTarget: IntArray = intArrayOf(0,1,2,4,3)

    @JvmStatic public fun evaluate(snapshot: CapabilitySnapshot): CapabilityReport = evaluate(snapshot, RangeFormatOptions())
    @JvmStatic public fun evaluate(snapshot: CapabilitySnapshot, options: RangeFormatOptions): CapabilityReport {
        require(snapshot.generation in 0..0xffffffffL) { "generation must be an unsigned 32-bit value" }
        val cs = snapshot.characteristics
        for (c in cs) validate(c)
        val kinds = cs.map { kindOf(it.uuid) }
        val first = IntArray(16) { -1 }; val counts = IntArray(16)
        kinds.forEachIndexed { i, k -> if (k != KnownCharacteristicKind.UNKNOWN) { val n = k.ordinal; if (first[n] < 0) first[n] = i; counts[n] = minOf(2, counts[n] + 1) } }
        val scopeOk = snapshot.scope == ServiceScope.PRESENT
        val presence = MutableList(16) { Presence.UNKNOWN }; val diagnostics = mutableListOf<CapabilityDiagnostic>()
        for (n in 1..15) when (counts[n]) { 2 -> { presence[n] = Presence.AMBIGUOUS; diagnostics += diag(DiagnosticCode.DUPLICATE_CHARACTERISTIC, kind(n), first[n]) }; 1 -> presence[n] = Presence.UNIQUE; else -> if (scopeOk && snapshot.discovery == DiscoveryState.COMPLETE) presence[n] = Presence.ABSENT }
        val absent = snapshot.scope == ServiceScope.ABSENT && snapshot.discovery == DiscoveryState.COMPLETE && cs.isEmpty()
        if (!scopeOk) diagnostics += diag(DiagnosticCode.SCOPE_UNAVAILABLE, KnownCharacteristicKind.UNKNOWN, null)
        if (snapshot.scope == ServiceScope.ABSENT && !absent) diagnostics += diag(DiagnosticCode.SCOPE_CONTRADICTION, KnownCharacteristicKind.UNKNOWN, null)
        if (snapshot.discovery != DiscoveryState.COMPLETE) diagnostics += diag(if (snapshot.discovery == DiscoveryState.FAILED) DiagnosticCode.DISCOVERY_FAILED else DiagnosticCode.DISCOVERY_INCOMPLETE, KnownCharacteristicKind.UNKNOWN, null)
        cs.forEachIndexed { i, c ->
            val k = kinds[i]; if (k == KnownCharacteristicKind.UNKNOWN || !scopeOk) return@forEachIndexed
            val expected = requiredProperties(k, snapshot.c7)
            val unknownC7 = k == KnownCharacteristicKind.FEATURE && c7Unknown(snapshot.c7)
            if ((c.properties and expected) != expected) diagnostics += diag(DiagnosticCode.REQUIRED_PROPERTY_MISSING, k, i)
            val permitted = expected or if (unknownC7) INDICATE else 0
            if ((c.properties and permitted.inv()) != 0) diagnostics += diag(DiagnosticCode.EXCLUDED_PROPERTY_PRESENT, k, i)
            if (unknownC7) diagnostics += diag(DiagnosticCode.C7_EVIDENCE_INSUFFICIENT, k, i)
            if (c.readState == ReadState.FAILED) diagnostics += diag(if (c.readReason == ReadReason.SECURITY_REQUIRED) DiagnosticCode.READ_SECURITY_REQUIRED else DiagnosticCode.READ_FAILED, k, i)
        }
        val featureIndex = if (scopeOk && presence[1] == Presence.UNIQUE) first[1] else -1
        val decodedFeature = if (featureIndex >= 0) decodeFeature(cs[featureIndex]) else DecodedFeature(DecodeState.NOT_ATTEMPTED,0,0)
        val feature = FeatureEvidence(presence[1], decodedFeature.state, featureIndex.takeIf { it >= 0 }, decodedFeature.machine, decodedFeature.target, decodedFeature.machine and 0xfffe0000L, decodedFeature.target and 0xfffe0000L)
        if (decodedFeature.state == DecodeState.MALFORMED) diagnostics += diag(DiagnosticCode.MALFORMED_BYTES, KnownCharacteristicKind.FEATURE, featureIndex)
        val ranges = (0..4).map { r ->
            val n = 9 + r; val index = if (scopeOk && presence[n] == Presence.UNIQUE) first[n] else -1
            val decoded = if (index >= 0) decodeRange(cs[index], RangeKind.entries[r], options) else DecodedRange(DecodeState.NOT_ATTEMPTED, null)
            if (decoded.state == DecodeState.MALFORMED) diagnostics += diag(DiagnosticCode.MALFORMED_BYTES, kind(n), index)
            RangeEvidence(presence[n], decoded.state, index.takeIf { it >= 0 }, decoded.value)
        }
        if (scopeOk) {
            if (presence[1] == Presence.ABSENT) diagnostics += diag(DiagnosticCode.REQUIRED_CHARACTERISTIC_MISSING, KnownCharacteristicKind.FEATURE, null)
            if ((presence[14] == Presence.UNIQUE || presence[14] == Presence.AMBIGUOUS) && presence[15] == Presence.ABSENT) diagnostics += diag(DiagnosticCode.REQUIRED_CHARACTERISTIC_MISSING, KnownCharacteristicKind.MACHINE_STATUS, null)
            if (decodedFeature.state == DecodeState.VALID) {
                if ((decodedFeature.target and 0x1ffffL) != 0L && presence[14] == Presence.ABSENT) diagnostics += diag(DiagnosticCode.REQUIRED_CHARACTERISTIC_MISSING, KnownCharacteristicKind.CONTROL_POINT, null)
                for (bit in 0..4) { val r = rangeForTarget[bit]; if ((decodedFeature.target and (1L shl bit)) != 0L && presence[9 + r] == Presence.ABSENT) diagnostics += diag(DiagnosticCode.REQUIRED_RANGE_MISSING, kind(9 + r), null) }
            }
        }
        val operations = (0..20).map { opcode -> operation(opcode, snapshot, cs, presence, first, decodedFeature, ranges, absent) }
        val observations = cs.mapIndexed { i, c -> Observation(i, c.uuid, c.properties, kinds[i], c.readState, c.readReason, c.bytesInternal().size) }
        return CapabilityReport(snapshot.generation, snapshot.discovery, snapshot.scope, observations.size, diagnostics.size, presence, feature, ranges, operations, observations, diagnostics)
    }

    private fun operation(opcode: Int, s: CapabilitySnapshot, cs: List<CharacteristicEvidence>, p: List<Presence>, first: IntArray, feature: DecodedFeature, ranges: List<RangeEvidence>, absent: Boolean): OperationEvidence {
        val bit = targetForOpcode[opcode]; var declaration = Declaration.UNKNOWN; var prerequisite = Prerequisite.INCOMPLETE; var reasons = 0
        if (s.scope != ServiceScope.PRESENT) { reasons = 1; if (absent) { declaration = Declaration.NOT_SUPPORTED; prerequisite = Prerequisite.NOT_APPLICABLE } else if (s.scope == ServiceScope.ABSENT) prerequisite = Prerequisite.INCONSISTENT; return OperationEvidence(opcode, bit.takeUnless { it == 255 }, opcode == 18 || opcode == 19, declaration, prerequisite, reasons) }
        if (bit == 255) declaration = if (p[14] == Presence.UNIQUE) Declaration.SUPPORTED else if (p[14] == Presence.ABSENT) Declaration.NOT_SUPPORTED else Declaration.UNKNOWN
        else if (feature.state == DecodeState.VALID) declaration = if ((feature.target and (1L shl bit)) != 0L) Declaration.SUPPORTED else Declaration.NOT_SUPPORTED
        if (declaration == Declaration.NOT_SUPPORTED) return OperationEvidence(opcode, bit.takeUnless { it == 255 }, opcode == 18 || opcode == 19, declaration, Prerequisite.NOT_APPLICABLE, 0)
        if (s.discovery != DiscoveryState.COMPLETE) reasons = reasons or 2
        reasons = reasons or characteristicReasons(1,p,first,cs,s.c7,4,8)
        if (bit != 255 && p[1] == Presence.UNIQUE) reasons = reasons or decodeReasons(feature.state,4,8)
        reasons = reasons or characteristicReasons(14,p,first,cs,s.c7,16,32) or characteristicReasons(15,p,first,cs,s.c7,64,128)
        if (bit in 0..4 && declaration == Declaration.SUPPORTED) { val r = rangeForTarget[bit]; reasons = reasons or characteristicReasons(9+r,p,first,cs,s.c7,256,512); if (p[9+r] == Presence.UNIQUE) reasons = reasons or decodeReasons(ranges[r].decode,256,512) }
        prerequisite = if ((reasons and (8 or 32 or 128 or 512)) != 0) Prerequisite.INCONSISTENT else if (reasons == 0) Prerequisite.SATISFIED else Prerequisite.INCOMPLETE
        return OperationEvidence(opcode, bit.takeUnless { it == 255 }, opcode == 18 || opcode == 19, declaration, prerequisite, reasons)
    }

    private fun characteristicReasons(kind: Int, p: List<Presence>, first: IntArray, cs: List<CharacteristicEvidence>, c7: C7Evidence?, unavailable: Int, invalid: Int): Int {
        if (p[kind] == Presence.UNKNOWN) return unavailable; if (p[kind] != Presence.UNIQUE) return invalid
        val props = cs[first[kind]].properties
        if (kind == 1 && c7Unknown(c7)) return 1024 or if ((props and READ) == 0 || (props and (READ or INDICATE).inv()) != 0) invalid else 0
        return if (props == requiredProperties(kind(kind),c7)) 0 else invalid
    }
    private fun decodeReasons(state: DecodeState, unavailable: Int, invalid: Int): Int = when (state) { DecodeState.VALID -> 0; DecodeState.MALFORMED -> invalid; else -> unavailable }
    private fun requiredProperties(kind: KnownCharacteristicKind, c7: C7Evidence?): Int = when (kind) { KnownCharacteristicKind.FEATURE -> READ or if (c7?.bondingSupported == TruthValue.TRUE && c7.featureMayChangeOverLifetime == TruthValue.TRUE) INDICATE else 0; KnownCharacteristicKind.TRAINING_STATUS -> READ or NOTIFY; KnownCharacteristicKind.CONTROL_POINT -> WRITE or INDICATE; KnownCharacteristicKind.SPEED_RANGE, KnownCharacteristicKind.INCLINATION_RANGE, KnownCharacteristicKind.RESISTANCE_RANGE, KnownCharacteristicKind.HEART_RATE_RANGE, KnownCharacteristicKind.POWER_RANGE -> READ; else -> NOTIFY }
    private fun c7Unknown(c7: C7Evidence?): Boolean = c7 == null || (c7.bondingSupported != TruthValue.FALSE && c7.featureMayChangeOverLifetime != TruthValue.FALSE && !(c7.bondingSupported == TruthValue.TRUE && c7.featureMayChangeOverLifetime == TruthValue.TRUE))
    private fun validate(c: CharacteristicEvidence) { require(c.uuid.matches(Regex("[0-9a-f]{32}"))) { "uuid must be 32 lowercase hexadecimal characters" }; require(c.properties in 0..0xffff) { "properties must be unsigned 16-bit" }; require(c.readState == ReadState.FAILED || c.readReason == ReadReason.NONE) { "read reason is valid only for failed reads" }; require(c.readState == ReadState.SUCCESS || c.bytesInternal().isEmpty()) { "bytes are valid only for successful reads" } }
    private fun kindOf(uuid: String): KnownCharacteristicKind { if (!uuid.startsWith("0000") || !uuid.endsWith("00001000800000805f9b34fb")) return KnownCharacteristicKind.UNKNOWN; val n = uuid.substring(4,8).toInt(16); return if (n in 0x2acc..0x2ada) KnownCharacteristicKind.entries[n - 0x2acc + 1] else KnownCharacteristicKind.UNKNOWN }
    private data class DecodedFeature(val state: DecodeState, val machine: Long, val target: Long)
    private data class DecodedRange(val state: DecodeState, val value: RangeValue?)
    private fun decodeFeature(c: CharacteristicEvidence): DecodedFeature { if (c.readState == ReadState.FAILED) return DecodedFeature(DecodeState.FAILED,0,0); if (c.readState != ReadState.SUCCESS) return DecodedFeature(DecodeState.NOT_ATTEMPTED,0,0); val b=c.bytesInternal(); if(b.size!=8)return DecodedFeature(DecodeState.MALFORMED,0,0); return DecodedFeature(DecodeState.VALID,u32(b,0),u32(b,4)) }
    private fun decodeRange(c: CharacteristicEvidence, kind: RangeKind, options: RangeFormatOptions): DecodedRange { if(c.readState==ReadState.FAILED)return DecodedRange(DecodeState.FAILED,null);if(c.readState!=ReadState.SUCCESS)return DecodedRange(DecodeState.NOT_ATTEMPTED,null);val b=c.bytesInternal();val alternate=kind==RangeKind.RESISTANCE&&options.resistanceRangeFormat==ResistanceRangeFormat.SINT16_TENTHS;val length=if(kind==RangeKind.HEART_RATE||kind==RangeKind.RESISTANCE&&!alternate)3 else 6;if(b.size!=length)return DecodedRange(DecodeState.MALFORMED,null);val min=if(length==3)u8(b,0) else if(kind==RangeKind.INCLINATION||kind==RangeKind.POWER||alternate)i16(b,0) else u16(b,0);val max=if(length==3)u8(b,1) else if(kind==RangeKind.INCLINATION||kind==RangeKind.POWER||alternate)i16(b,2) else u16(b,2);val inc=if(length==3)u8(b,2) else u16(b,4);if(min>max||inc==0)return DecodedRange(DecodeState.MALFORMED,null);val divisor=when(kind){RangeKind.SPEED->100;RangeKind.INCLINATION->10;RangeKind.RESISTANCE->if(alternate)10 else 1;else->1};val unit=arrayOf("km/h","percent","level","bpm","watts")[kind.ordinal];return DecodedRange(DecodeState.VALID,RangeValue(kind,min,max,inc,divisor,unit)) }
    private fun u8(b:ByteArray,o:Int):Int=b[o].toInt()and 255; private fun u16(b:ByteArray,o:Int):Int=u8(b,o)or(u8(b,o+1)shl 8); private fun i16(b:ByteArray,o:Int):Int=u16(b,o).let{if(it>=0x8000)it-0x10000 else it}; private fun u32(b:ByteArray,o:Int):Long=(u16(b,o).toLong() or (u16(b,o+2).toLong() shl 16))
    private fun kind(n:Int):KnownCharacteristicKind=KnownCharacteristicKind.entries[n]; private fun diag(c:DiagnosticCode,k:KnownCharacteristicKind,i:Int?):CapabilityDiagnostic=CapabilityDiagnostic(c,k,i)
}

private fun <T> immutableCopy(values: List<T>): List<T> = Collections.unmodifiableList(ArrayList(values))
