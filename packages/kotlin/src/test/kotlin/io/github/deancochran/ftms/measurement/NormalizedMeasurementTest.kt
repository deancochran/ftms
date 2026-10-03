package io.github.deancochran.ftms.measurement

import java.util.UUID
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

class NormalizedMeasurementTest {
    private fun uuid(short: String): UUID = UUID.fromString("0000$short-0000-1000-8000-00805f9b34fb")

    @Test fun `universal reader covers all families and diagnostics`() {
        val packets = listOf(byteArrayOf(0,0,0x10,0x0e), byteArrayOf(0,0,0,0x10,0x0e), byteArrayOf(0,0,1,0,2,0), byteArrayOf(0,0,1,0), byteArrayOf(0,0,7,1,0,2,0), byteArrayOf(0,0,0x10,0x0e))
        listOf("2acd","2ace","2acf","2ad0","2ad1","2ad2").forEachIndexed { index, short ->
            val decoded = assertIs<MeasurementDecodeResult.Decoded>(MeasurementReader.decode(uuid(short), packets[index]))
            assertEquals(MeasurementKind.entries[index], decoded.measurement.raw.kind)
            val truncated = assertIs<MeasurementDecodeResult.Decoded>(MeasurementReader.decode(uuid(short), packets[index].copyOf(if(index == 1) 3 else 2)))
            assertTrue(truncated.measurement.raw.truncated)
        }
        val unavailable = assertIs<MeasurementDecodeResult.Decoded>(MeasurementReader.decode(uuid("2acd"), byteArrayOf(8,0,0,0,(-1).toByte(),0x7f,(-1).toByte(),0x7f)))
        assertNull(unavailable.measurement.inclinationPercent); assertTrue(unavailable.measurement.raw.unavailable and (1L shl MeasurementField.INCLINATION) != 0L)
        val reserved = assertIs<MeasurementDecodeResult.Decoded>(MeasurementReader.decode(uuid("2acd"), byteArrayOf(0,0x20,0,0)))
        assertTrue(reserved.measurement.raw.reservedFlags)
    }

    @Test fun `formats preserve provenance and unknown UUIDs do not guess`() {
        val unsigned = assertIs<MeasurementDecodeResult.Decoded>(MeasurementReader.decode(uuid("2ace"), byteArrayOf(0x80.toByte(),0,0,0,0,9)))
        assertEquals(9.0, unsigned.measurement.resistanceLevel)
        val signed = assertIs<MeasurementDecodeResult.Decoded>(MeasurementReader.decode(uuid("2ace"), byteArrayOf(0x80.toByte(),0,0,0,0,0xfb.toByte(),(-1).toByte()), MeasurementFormat(ResistanceFormat.SINT16_TENTHS)))
        assertEquals(-0.5, signed.measurement.resistanceLevel); assertEquals(ResistanceFormat.SINT16_TENTHS, signed.measurement.format.resistance)
        val legacy = assertIs<MeasurementDecodeResult.Decoded>(MeasurementReader.decode(uuid("2acd"), byteArrayOf(0x20,0,0,0,12), MeasurementFormat(treadmillPace = TreadmillPaceFormat.UINT8_LEGACY)))
        assertNull(legacy.measurement.instantaneousPaceSecondsPer500m); assertEquals(12, legacy.measurement.raw.valueAt(MeasurementField.INSTANTANEOUS_PACE))
        assertIs<MeasurementDecodeResult.Unsupported>(MeasurementReader.decode(UUID(0x12, 0), byteArrayOf(0,0)))
        assertIs<MeasurementDecodeResult.Unsupported>(MeasurementReader.decode(uuid("2ad3"), byteArrayOf(0,0)))
        assertIs<MeasurementDecodeResult.Invalid>(MeasurementReader.decode(uuid("2acd"), byteArrayOf(0)))
    }

    @Test fun `all field physical goldens cover each normalized metric`() {
        val allFields = listOf(
            (0..17).toList(), listOf(0,1,2,18,19,20,5,6,3,4,21,17,22,9,10,11,12,13,14,15),
            listOf(23,24,18,19,5,9,10,11,12,13,14,15), listOf(23,18,19,5,20,9,10,11,12,13,14,15),
            listOf(25,26,27,2,7,8,17,22,21,9,10,11,12,13,14,15), listOf(0,1,28,29,2,21,17,22,9,10,11,12,13,14,15),
        )
        val flags = listOf(0x1ffe, 0xfffe, 0x1fe, 0x3fe, 0x1ffe, 0x1ffe)
        listOf("2acd","2ace","2acf","2ad0","2ad1","2ad2").forEachIndexed { kind, short ->
            val fields = allFields[kind]; val values = IntArray(MeasurementField.COUNT) { 100 + it }
            val present = fields.fold(0L) { mask, field -> mask or (1L shl field) }
            val raw = Measurement(MeasurementKind.entries[kind], flags[kind], present, 0, values)
            val bytes = MeasurementCodec.encode(raw)
            val reading = assertIs<MeasurementDecodeResult.Decoded>(MeasurementReader.decode(uuid(short), bytes)).measurement
            fun expected(field: Int, divisor: Double): Double? = if (field in fields) (100 + field) / divisor else null
            fun metric(name: String, actual: Double?, expected: Double?) = assertEquals(expected, actual, "kind=$kind $name")
            metric("speed", reading.speedMps, expected(MeasurementField.SPEED,360.0)); metric("averageSpeed", reading.averageSpeedMps, expected(MeasurementField.AVERAGE_SPEED,360.0)); metric("distance", reading.distanceMeters, expected(MeasurementField.DISTANCE,1.0))
            metric("inclination", reading.inclinationPercent, expected(MeasurementField.INCLINATION,10.0)); metric("ramp", reading.rampAngleDegrees, expected(MeasurementField.RAMP_ANGLE,10.0))
            val elevation = if (kind == MeasurementKind.TREADMILL.ordinal) 10.0 else 1.0
            metric("positiveElevation", reading.positiveElevationGainMeters, expected(MeasurementField.POSITIVE_ELEVATION,elevation)); metric("negativeElevation", reading.negativeElevationGainMeters, expected(MeasurementField.NEGATIVE_ELEVATION,elevation))
            metric("instantaneousPace", reading.instantaneousPaceSecondsPer500m, expected(MeasurementField.INSTANTANEOUS_PACE,1.0)); metric("averagePace", reading.averagePaceSecondsPer500m, expected(MeasurementField.AVERAGE_PACE,1.0))
            metric("energy", reading.energyKcal, expected(MeasurementField.TOTAL_ENERGY,1.0)); metric("energyPerHour", reading.energyPerHourKcal, expected(MeasurementField.ENERGY_PER_HOUR,1.0)); metric("energyPerMinute", reading.energyPerMinuteKcal, expected(MeasurementField.ENERGY_PER_MINUTE,1.0)); metric("heartRate", reading.heartRateBpm, expected(MeasurementField.HEART_RATE,1.0))
            metric("met", reading.metabolicEquivalent, expected(MeasurementField.MET,10.0)); metric("elapsed", reading.elapsedTimeSeconds, expected(MeasurementField.ELAPSED_TIME,1.0)); metric("remaining", reading.remainingTimeSeconds, expected(MeasurementField.REMAINING_TIME,1.0)); metric("force", reading.forceOnBeltNewtons, expected(MeasurementField.FORCE_ON_BELT,1.0)); metric("power", reading.powerWatts, expected(MeasurementField.POWER,1.0))
            metric("stepRate", reading.stepRateSpm, expected(MeasurementField.STEP_RATE,1.0)); metric("averageStepRate", reading.averageStepRateSpm, expected(MeasurementField.AVERAGE_STEP_RATE,1.0)); metric("stride", reading.strideCount, expected(MeasurementField.STRIDE_COUNT,if(kind == MeasurementKind.CROSS_TRAINER.ordinal)10.0 else 1.0))
            metric("resistance", reading.resistanceLevel, expected(MeasurementField.RESISTANCE,1.0)); metric("averagePower", reading.averagePowerWatts, expected(MeasurementField.AVERAGE_POWER,1.0)); metric("floor", reading.floorCount, expected(MeasurementField.FLOOR_COUNT,1.0)); metric("stepCount", reading.stepCount, expected(MeasurementField.STEP_COUNT,1.0))
            metric("strokeRate", reading.strokeRateSpm, expected(MeasurementField.STROKE_RATE,2.0)); metric("strokeCount", reading.strokeCount, expected(MeasurementField.STROKE_COUNT,1.0)); metric("averageStrokeRate", reading.averageStrokeRateSpm, expected(MeasurementField.AVERAGE_STROKE_RATE,2.0)); metric("cadence", reading.cadenceRpm, expected(MeasurementField.CADENCE,2.0)); metric("averageCadence", reading.averageCadenceRpm, expected(MeasurementField.AVERAGE_CADENCE,2.0))
            if (kind == MeasurementKind.CROSS_TRAINER.ordinal) assertEquals(MovementDirection.BACKWARD, reading.movementDirection) else assertNull(reading.movementDirection)
        }
    }
}
