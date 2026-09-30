package io.github.deancochran.ftms.measurement

import org.junit.jupiter.api.Assertions.assertArrayEquals
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class MeasurementCodecTest {
    @Test fun `measurement values retain independent ownership`() {
        val values = IntArray(30).also { it[0] = 123 }
        val measurement = Measurement(MeasurementKind.TREADMILL, 0, 1L, 0L, values)
        values[0] = 0; measurement.values[0] = 0
        assertEquals(123, measurement.valueAt(0))
        val bytes = byteArrayOf(0, 0, 123, 0)
        val decoded = MeasurementCodec.decode(MeasurementKind.TREADMILL, bytes)
        bytes[2] = 0; decoded.values[0] = 0
        assertEquals(123, decoded.valueAt(0))
        assertArrayEquals(byteArrayOf(0, 0, 123, 0), MeasurementCodec.encode(measurement))
    }
    @Test fun `all six mandatory layouts encode and decode literal bytes`() {
        val cases = listOf(
            MeasurementKind.TREADMILL to byteArrayOf(0, 0, 0x34, 0x12),
            MeasurementKind.CROSS_TRAINER to byteArrayOf(0, 0, 0, 0x34, 0x12),
            MeasurementKind.STEP_CLIMBER to byteArrayOf(0, 0, 0x34, 0x12, 0x78, 0x56),
            MeasurementKind.STAIR_CLIMBER to byteArrayOf(0, 0, 0x34, 0x12),
            MeasurementKind.ROWER to byteArrayOf(0, 0, 7, 0x34, 0x12),
            MeasurementKind.INDOOR_BIKE to byteArrayOf(0, 0, 0x34, 0x12),
        )
        for ((kind, bytes) in cases) {
            val decoded = MeasurementCodec.decode(kind, bytes)
            assertEquals(bytes.size, decoded.bytesRead)
            assertEquals(false, decoded.truncated)
            val fields = when (kind) {
                MeasurementKind.STEP_CLIMBER -> mapOf(23 to 0x1234, 24 to 0x5678)
                MeasurementKind.STAIR_CLIMBER -> mapOf(23 to 0x1234)
                MeasurementKind.ROWER -> mapOf(25 to 7, 26 to 0x1234)
                else -> mapOf(0 to 0x1234)
            }
            val values = IntArray(30)
            var present = 0L
            fields.forEach { (field, value) -> values[field] = value; present = present or (1L shl field) }
            assertArrayEquals(bytes, MeasurementCodec.encode(Measurement(kind, 0, present, 0L, values)))
        }
    }

    @Test fun `selected compatibility formats consume their literal widths`() {
        val treadmill = MeasurementCodec.decode(MeasurementKind.TREADMILL, byteArrayOf(0x60, 0, 0, 0, 1, 2), MeasurementFormat(treadmillPace = TreadmillPaceFormat.UINT8_LEGACY))
        assertEquals(1, treadmill.valueAt(MeasurementField.INSTANTANEOUS_PACE)); assertEquals(2, treadmill.valueAt(MeasurementField.AVERAGE_PACE)); assertEquals(6, treadmill.bytesRead)
        val bikeBytes = byteArrayOf(0x20, 0, 0, 0, 0x85.toByte(), 0xff.toByte())
        val bike = MeasurementCodec.decode(MeasurementKind.INDOOR_BIKE, bikeBytes, MeasurementFormat(resistance = ResistanceFormat.SINT16_TENTHS))
        assertEquals(-123, bike.valueAt(MeasurementField.RESISTANCE))
        val expected = Measurement(MeasurementKind.INDOOR_BIKE, 0x20, 1L or (1L shl 21), 0L, IntArray(30).also { it[21] = -123 })
        assertArrayEquals(bikeBytes, MeasurementCodec.encode(expected, MeasurementFormat(resistance = ResistanceFormat.SINT16_TENTHS)))
    }

    @Test fun `reserved flags and incomplete groups remain diagnostics but cannot encode`() {
        val decoded = MeasurementCodec.decode(MeasurementKind.TREADMILL, byteArrayOf(0, 0x20, 1))
        assertEquals(true, decoded.reservedFlags); assertEquals(true, decoded.truncated); assertEquals(2, decoded.bytesRead)
        assertThrows(IllegalArgumentException::class.java) { MeasurementCodec.encode(decoded) }
    }
}
