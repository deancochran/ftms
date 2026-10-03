package io.github.deancochran.ftms.measurement

import java.util.UUID

/** A physical-unit measurement view. Null means absent, unavailable, or incomplete; [raw] preserves that distinction. */
public data class NormalizedMeasurement(
    public val raw: Measurement, public val format: MeasurementFormat,
    /** Present only for Cross Trainer Data; other families do not encode direction. */
    public val movementDirection: MovementDirection? = null,
    public val speedMps: Double? = null, public val averageSpeedMps: Double? = null, public val distanceMeters: Double? = null,
    public val inclinationPercent: Double? = null, public val rampAngleDegrees: Double? = null,
    public val positiveElevationGainMeters: Double? = null, public val negativeElevationGainMeters: Double? = null,
    public val instantaneousPaceSecondsPer500m: Double? = null, public val averagePaceSecondsPer500m: Double? = null,
    public val energyKcal: Double? = null, public val energyPerHourKcal: Double? = null, public val energyPerMinuteKcal: Double? = null,
    public val heartRateBpm: Double? = null, public val metabolicEquivalent: Double? = null, public val elapsedTimeSeconds: Double? = null,
    public val remainingTimeSeconds: Double? = null, public val forceOnBeltNewtons: Double? = null, public val powerWatts: Double? = null,
    public val stepRateSpm: Double? = null, public val averageStepRateSpm: Double? = null, public val strideCount: Double? = null,
    public val resistanceLevel: Double? = null, public val averagePowerWatts: Double? = null, public val floorCount: Double? = null,
    public val stepCount: Double? = null, public val strokeRateSpm: Double? = null, public val strokeCount: Double? = null,
    public val averageStrokeRateSpm: Double? = null, public val cadenceRpm: Double? = null, public val averageCadenceRpm: Double? = null,
)

/** Named Cross Trainer Data direction. */
public enum class MovementDirection { FORWARD, BACKWARD }

/** Typed outcome for the UUID-selected convenience decoder; raw codec APIs continue to throw for invalid layouts. */
public sealed interface MeasurementDecodeResult {
    public data class Decoded(public val measurement: NormalizedMeasurement) : MeasurementDecodeResult
    public data class Unsupported(public val characteristicUuid: UUID) : MeasurementDecodeResult
    public data class Invalid(public val error: IllegalArgumentException) : MeasurementDecodeResult
}

/** UUID-selected, format-explicit measurement projection. Exact Bluetooth-base UUID matching prevents alias guessing. */
public object MeasurementReader {
    private val kinds: Map<UUID, MeasurementKind> = mapOf(
        UUID.fromString("00002acd-0000-1000-8000-00805f9b34fb") to MeasurementKind.TREADMILL,
        UUID.fromString("00002ace-0000-1000-8000-00805f9b34fb") to MeasurementKind.CROSS_TRAINER,
        UUID.fromString("00002acf-0000-1000-8000-00805f9b34fb") to MeasurementKind.STEP_CLIMBER,
        UUID.fromString("00002ad0-0000-1000-8000-00805f9b34fb") to MeasurementKind.STAIR_CLIMBER,
        UUID.fromString("00002ad1-0000-1000-8000-00805f9b34fb") to MeasurementKind.ROWER,
        UUID.fromString("00002ad2-0000-1000-8000-00805f9b34fb") to MeasurementKind.INDOOR_BIKE,
    )

    @JvmStatic @JvmOverloads public fun decode(characteristicUuid: UUID, bytes: ByteArray, format: MeasurementFormat = MeasurementFormat()): MeasurementDecodeResult {
        val kind = kinds[characteristicUuid] ?: return MeasurementDecodeResult.Unsupported(characteristicUuid)
        val raw = try { MeasurementCodec.decode(kind, bytes, format) } catch (error: IllegalArgumentException) { return MeasurementDecodeResult.Invalid(error) }
        fun value(field: Int, divisor: Double): Double? = if (
            raw.present and (1L shl field) != 0L && raw.unavailable and (1L shl field) == 0L
        ) raw.valueAt(field) / divisor else null
        val pace = !(kind == MeasurementKind.TREADMILL && format.treadmillPace == TreadmillPaceFormat.UINT8_LEGACY)
        val resistance = if (format.resistance == ResistanceFormat.SINT16_TENTHS) 10.0 else 1.0
        val elevation = if (kind == MeasurementKind.TREADMILL) 10.0 else 1.0
        return MeasurementDecodeResult.Decoded(NormalizedMeasurement(
            raw = raw,
            format = format,
            movementDirection = if (kind == MeasurementKind.CROSS_TRAINER) {
                if (raw.backward) MovementDirection.BACKWARD else MovementDirection.FORWARD
            } else null,
            speedMps = value(MeasurementField.SPEED, 360.0),
            averageSpeedMps = value(MeasurementField.AVERAGE_SPEED, 360.0),
            distanceMeters = value(MeasurementField.DISTANCE, 1.0),
            inclinationPercent = value(MeasurementField.INCLINATION, 10.0),
            rampAngleDegrees = value(MeasurementField.RAMP_ANGLE, 10.0),
            positiveElevationGainMeters = value(MeasurementField.POSITIVE_ELEVATION, elevation),
            negativeElevationGainMeters = value(MeasurementField.NEGATIVE_ELEVATION, elevation),
            instantaneousPaceSecondsPer500m = if (pace) value(MeasurementField.INSTANTANEOUS_PACE, 1.0) else null,
            averagePaceSecondsPer500m = if (pace) value(MeasurementField.AVERAGE_PACE, 1.0) else null,
            energyKcal = value(MeasurementField.TOTAL_ENERGY, 1.0),
            energyPerHourKcal = value(MeasurementField.ENERGY_PER_HOUR, 1.0),
            energyPerMinuteKcal = value(MeasurementField.ENERGY_PER_MINUTE, 1.0),
            heartRateBpm = value(MeasurementField.HEART_RATE, 1.0),
            metabolicEquivalent = value(MeasurementField.MET, 10.0),
            elapsedTimeSeconds = value(MeasurementField.ELAPSED_TIME, 1.0),
            remainingTimeSeconds = value(MeasurementField.REMAINING_TIME, 1.0),
            forceOnBeltNewtons = value(MeasurementField.FORCE_ON_BELT, 1.0),
            powerWatts = value(MeasurementField.POWER, 1.0),
            stepRateSpm = value(MeasurementField.STEP_RATE, 1.0),
            averageStepRateSpm = value(MeasurementField.AVERAGE_STEP_RATE, 1.0),
            strideCount = value(MeasurementField.STRIDE_COUNT, if (kind == MeasurementKind.CROSS_TRAINER) 10.0 else 1.0),
            resistanceLevel = value(MeasurementField.RESISTANCE, resistance),
            averagePowerWatts = value(MeasurementField.AVERAGE_POWER, 1.0),
            floorCount = value(MeasurementField.FLOOR_COUNT, 1.0),
            stepCount = value(MeasurementField.STEP_COUNT, 1.0),
            strokeRateSpm = value(MeasurementField.STROKE_RATE, 2.0),
            strokeCount = value(MeasurementField.STROKE_COUNT, 1.0),
            averageStrokeRateSpm = value(MeasurementField.AVERAGE_STROKE_RATE, 2.0),
            cadenceRpm = value(MeasurementField.CADENCE, 2.0),
            averageCadenceRpm = value(MeasurementField.AVERAGE_CADENCE, 2.0),
        ))
    }
}
