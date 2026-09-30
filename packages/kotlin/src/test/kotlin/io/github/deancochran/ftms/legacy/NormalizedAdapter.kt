package io.github.deancochran.ftms.legacy

import com.google.gson.JsonObject
import io.github.deancochran.ftms.*
import io.github.deancochran.ftms.measurement.*
import io.github.deancochran.ftms.status.*

internal fun JsonObject.bytes(): ByteArray = getAsJsonArray("bytes").map { it.asInt.toByte() }.toByteArray()
internal fun JsonObject.text(key: String): String = get(key).asString
internal fun JsonObject.int(key: String): Int = get(key).asInt
internal fun kind(name: String): RangeKind = when(name) {
    "speed" -> RangeKind.SPEED; "inclination" -> RangeKind.INCLINATION; "resistance" -> RangeKind.RESISTANCE
    "heartRate" -> RangeKind.HEART_RATE; "power" -> RangeKind.POWER; else -> error("Unknown range $name")
}
internal fun kindName(kind: RangeKind): String = when(kind) {
    RangeKind.SPEED -> "speed"; RangeKind.INCLINATION -> "inclination"; RangeKind.RESISTANCE -> "resistance"
    RangeKind.HEART_RATE -> "heartRate"; RangeKind.POWER -> "power"
}

/** All mappings are protocol field mappings, independent of fixture expected values. */
internal object NormalizedAdapter {
    private val machine = listOf("averageSpeedSupported", "cadenceSupported", "totalDistanceSupported", "inclinationSupported",
        "elevationGainSupported", "paceSupported", "stepCountSupported", "resistanceLevelSupported", "strideCountSupported",
        "expendedEnergySupported", "heartRateMeasurementSupported", "metabolicEquivalentSupported", "elapsedTimeSupported",
        "remainingTimeSupported", "powerMeasurementSupported", "forceOnBeltSupported", "userDataRetentionSupported")
    private val target = listOf("speedTargetSettingSupported", "inclinationTargetSettingSupported", "resistanceTargetSettingSupported",
        "powerTargetSettingSupported", "heartRateTargetSettingSupported", "targetedExpendedEnergySupported", "targetedStepNumberSupported",
        "targetedStrideNumberSupported", "targetedDistanceSupported", "targetedTrainingTimeSupported", "targetedTimeTwoHRZonesSupported",
        "targetedTimeThreeHRZonesSupported", "targetedTimeFiveHRZonesSupported", "indoorBikeSimulationSupported", "wheelCircumferenceSupported",
        "spinDownControlSupported", "targetedCadenceSupported")
    fun features(bytes: ByteArray): Map<String, Boolean> {
        val raw = FeatureCodec.decode(bytes); val out = linkedMapOf<String, Boolean>()
        machine.forEachIndexed { i, name -> out[name] = raw.machine and (1L shl i) != 0L }
        target.forEachIndexed { i, name -> out[name] = raw.target and (1L shl i) != 0L }
        out["supportsERG"] = out.getValue("powerTargetSettingSupported")
        out["supportsSIM"] = out.getValue("indoorBikeSimulationSupported")
        out["supportsResistance"] = out.getValue("resistanceTargetSettingSupported")
        return out
    }
    fun range(name: String, bytes: ByteArray): Map<String, Any> {
        val r = RangeCodec.decode(kind(name), bytes)
        val unit = when(r.unit) { RangeUnit.KILOMETRES_PER_HOUR -> "km/h"; RangeUnit.PERCENT -> "percent"; RangeUnit.LEVEL -> "level"; RangeUnit.BEATS_PER_MINUTE -> "bpm"; RangeUnit.WATTS -> "watts" }
        return mapOf("kind" to kindName(r.kind), "min" to r.minimum.toDouble()/r.scaleDivisor,
            "max" to r.maximum.toDouble()/r.scaleDivisor, "increment" to r.increment.toDouble()/r.scaleDivisor, "unit" to unit)
    }
    private val operations = listOf("requestControl", "reset", "setTargetSpeed", "setTargetInclination", "setTargetResistance",
        "setTargetPower", "setTargetHeartRate", "startResume", "stopPause", "setTargetedExpendedEnergy", "setTargetedSteps",
        "setTargetedStrides", "setTargetedDistance", "setTargetedTrainingTime", "setTargetedTimeTwoHrZones", "setTargetedTimeThreeHrZones",
        "setTargetedTimeFiveHrZones", "setIndoorBikeSimulation", "setWheelCircumference", "spinDown", "setTargetedCadence")
    fun request(r: JsonObject): ByteArray {
        val op = operations.indexOf(r.text("op")); require(op >= 0)
        fun scaled(key: String, scale: Int = 1): Long = r[key].asBigDecimal.multiply(scale.toBigDecimal()).longValueExact()
        val scalar = mapOf(2 to ("speedKph" to 100), 3 to ("inclinationPercent" to 10), 4 to ("resistanceLevel" to 10),
            5 to ("powerWatts" to 1), 6 to ("heartRateBpm" to 1), 9 to ("energyKcal" to 1), 10 to ("steps" to 1),
            11 to ("strides" to 1), 12 to ("distanceMeters" to 1), 13 to ("seconds" to 1), 18 to ("circumferenceMm" to 10), 20 to ("cadenceRpm" to 2))
        val operands = when {
            op in scalar -> scalar.getValue(op).let { longArrayOf(scaled(it.first, it.second)) }
            op == 8 || op == 19 -> longArrayOf(when(r.text("action")) { "stop", "start" -> 1L; "pause", "ignore" -> 2L; else -> error("unknown action") })
            op in 14..16 -> r.getAsJsonArray("seconds").map { it.asLong }.toLongArray()
            op == 17 -> longArrayOf(scaled("windSpeedMps",1000), scaled("gradePercent",100), scaled("crr",10000), scaled("cwKgPerM",100))
            else -> longArrayOf()
        }
        return ControlCodec.encodeRequest(ControlRequest(op, operands))
    }
    fun response(bytes: ByteArray): Map<String, Any> {
        val r = ControlCodec.decodeResponse(bytes)
        // The raw evidence API retains these diagnostics; the v1 validated view rejects them.
        if (r.unknownRequest != 0 || r.unexpectedParameters != 0) throw FtmsException(FtmsError.KIND)
        val name = mapOf(1 to "success", 2 to "not_supported", 3 to "invalid_parameter", 4 to "operation_failed", 5 to "control_not_permitted")[r.resultCode]
            ?: "unknown_0x%02x".format(r.resultCode)
        val parameter = if(r.parameter == 1) mapOf("kind" to "spin_down_speeds", "targetSpeedLowKph" to r.low/100.0, "targetSpeedHighKph" to r.high/100.0)
            else { demand(r.parameter == 0, "unknown response parameter"); mapOf("kind" to "none") }
        return mapOf("requestOpCode" to r.requestOpcode, "resultCode" to r.resultCode, "resultCodeName" to name,
            "success" to (r.resultCode == 1), "parameter" to parameter, "issues" to if(r.unknownResult != 0) listOf("reserved_value") else emptyList<String>())
    }
    private val metricNames = listOf("speedMps", "averageSpeedMps", "distanceMeters", "inclinationPercent", "rampAngleDegrees",
        "positiveElevationGainMeters", "negativeElevationGainMeters", "instantaneousPaceSecondsPer500m", "averagePaceSecondsPer500m",
        "energyKcal", "energyPerHourKcal", "energyPerMinuteKcal", "hrBpm", "metabolicEquivalent", "elapsedTimeSeconds", "remainingTimeSeconds",
        "forceOnBeltNewtons", "powerWatts", "stepRateSpm", "averageStepRateSpm", "strideCount", "resistanceLevel", "averagePowerWatts",
        "floorCount", "stepCount", "strokeRateSpm", "strokeCount", "averageStrokeRateSpm", "cadenceRpm", "averageCadenceRpm")
    private val groups = listOf(
        listOf(listOf(0),listOf(1),listOf(2),listOf(3,4),listOf(5,6),listOf(7),listOf(8),listOf(9,10,11),listOf(12),listOf(13),listOf(14),listOf(15),listOf(16,17)),
        listOf(listOf(0),listOf(1),listOf(2),listOf(18,19),listOf(20),listOf(5,6),listOf(3,4),listOf(21),listOf(17),listOf(22),listOf(9,10,11),listOf(12),listOf(13),listOf(14),listOf(15)),
        listOf(listOf(23,24),listOf(18),listOf(19),listOf(5),listOf(9,10,11),listOf(12),listOf(13),listOf(14),listOf(15)),
        listOf(listOf(23),listOf(18),listOf(19),listOf(5),listOf(20),listOf(9,10,11),listOf(12),listOf(13),listOf(14),listOf(15)),
        listOf(listOf(25,26),listOf(27),listOf(2),listOf(7),listOf(8),listOf(17),listOf(22),listOf(21),listOf(9,10,11),listOf(12),listOf(13),listOf(14),listOf(15)),
        listOf(listOf(0),listOf(1),listOf(28),listOf(29),listOf(2),listOf(21),listOf(17),listOf(22),listOf(9,10,11),listOf(12),listOf(13),listOf(14),listOf(15)))
    fun measurementMetrics(r: Measurement): Map<String, Any?> {
        val out = linkedMapOf<String, Any?>()
        metricNames.forEachIndexed { i, name -> if(r.present and (1L shl i) != 0L) {
            val divisor = when { i in 0..1 -> 360; i in 3..4 || i == 13 -> 10; i in 5..6 && r.kind == MeasurementKind.TREADMILL -> 10
                i == 20 && r.kind == MeasurementKind.CROSS_TRAINER -> 10; i in listOf(25,27,28,29) -> 2; else -> 1 }
            out[name] = if(r.unavailable and (1L shl i) != 0L) null else r.valueAt(i).toDouble()/divisor
        } }
        // Flagged but unread fields are null in v1, not physically present in the raw API.
        if(r.truncated) groups[r.kind.ordinal].forEachIndexed { bit, fields ->
            if(if(bit == 0) r.flags and 1 == 0 else r.flags and (1 shl bit) != 0)
                fields.filter { r.present and (1L shl it) == 0L }.forEach { out[metricNames[it]] = null }
        }
        if(r.kind == MeasurementKind.CROSS_TRAINER) out["movementDirection"] = if(r.backward) "backward" else "forward"
        return out
    }
    data class Parsed(val metrics: Map<String, Any?> = emptyMap(), val status: Map<String, Any?> = emptyMap(), val truncated: Boolean, val issues: Set<String>)
    fun parse(uuid: String, bytes: ByteArray): Parsed {
        val measurementUuids = listOf("2acd", "2ace", "2acf", "2ad0", "2ad1", "2ad2").map { "0000$it-0000-1000-8000-00805f9b34fb" }
        val index = measurementUuids.indexOf(uuid)
        val issues = linkedSetOf<String>()
        fun issue(flag: Boolean, code: String) { if(flag) issues += code }
        if(index >= 0) {
            val r = MeasurementCodec.decode(MeasurementKind.entries[index], bytes)
            issue(r.moreData,"more_data"); issue(r.truncated,"truncated"); issue(r.trailingBytes,"trailing_bytes")
            issue(r.reservedFlags,"reserved_flags"); issue(r.unavailable != 0L,"unavailable")
            return Parsed(metrics = measurementMetrics(r), truncated = r.truncated, issues = issues)
        }
        if(uuid == "00002ad3-0000-1000-8000-00805f9b34fb") {
            val r = StatusCodec.decodeTraining(bytes)
            issue(r.truncated,"truncated"); issue(r.trailingBytes,"trailing_bytes"); issue(r.reservedFlags != 0,"reserved_flags")
            issue(r.reservedValue,"reserved_value"); issue(r.invalidFlags,"invalid_flags"); issue(r.invalidUtf8,"invalid_utf8")
            val status = mapOf("code" to if(r.truncated) null else r.code, "label" to if(r.code == 13) "manual_mode" else "unmapped_${r.code}",
                "details" to mapOf("kind" to "training_status", "flags" to r.flags, "stringPresent" to r.textPresent,
                    "extendedStringPresent" to r.extendedString, "trainingStatusString" to if(r.textPresent) r.text.toString(Charsets.UTF_8) else null))
            return Parsed(status = status, truncated = r.truncated, issues = issues)
        }
        require(uuid == "00002ada-0000-1000-8000-00805f9b34fb") { "Unsupported UUID $uuid" }
        val r = StatusCodec.decodeMachine(bytes)
        issue(r.truncated,"truncated"); issue(r.trailingBytes,"trailing_bytes"); issue(r.unknownOpcode,"unknown_opcode"); issue(r.reservedValue,"reserved_value")
        val p = r.parameter
        val (label, details) = when {
            r.opcode == 5 && p?.requestOpcode == 2 -> "target_speed_changed" to mapOf("kind" to "speed", "speedKph" to p.operandAt(0)/100.0)
            r.opcode == 18 && p?.requestOpcode == 17 -> "indoor_bike_simulation_parameters_changed" to mapOf("kind" to "simulation",
                "windSpeedMps" to p.operandAt(0)/1000.0, "gradePercent" to p.operandAt(1)/100.0, "crr" to p.operandAt(2)/10000.0, "cwKgPerM" to p.operandAt(3)/100.0)
            r.opcode == 255 && p == null -> "control_permission_lost" to mapOf("kind" to "none")
            else -> "unmapped_${r.opcode}" to mapOf("kind" to "unmapped")
        }
        return Parsed(status = mapOf("code" to if(r.truncated && r.unknownOpcode && r.opcode == 0) null else r.opcode,
            "label" to label, "details" to details), truncated = r.truncated, issues = issues)
    }
}
