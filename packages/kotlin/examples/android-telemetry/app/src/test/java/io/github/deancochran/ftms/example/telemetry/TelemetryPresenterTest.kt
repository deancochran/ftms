package io.github.deancochran.ftms.example.telemetry

import io.github.deancochran.ftms.measurement.ResistanceFormat
import io.github.deancochran.ftms.measurement.MeasurementDecodeResult
import io.github.deancochran.ftms.measurement.MeasurementReader
import java.util.UUID
import org.junit.Assert.*
import org.junit.Test

class TelemetryPresenterTest {
    @Test fun `valid packet presents speed cadence and power`() {
        // flags cadence, instantaneous power; speed is mandatory: 10 m/s, 90 rpm, 200 W.
        val state = TelemetryPresenter().decode(byteArrayOf(0x44, 0x00, 0x10, 0x0e, 0xb4.toByte(), 0x00, 0xc8.toByte(), 0x00))
        assertEquals("Speed 10.00 m/s", state.speed); assertEquals("Cadence 90.0 rpm", state.cadence); assertEquals("Power 200 W", state.power)
    }
    @Test fun `short flags and advertised missing field are rejected`() {
        assertTrue(TelemetryPresenter().decode(byteArrayOf(0)).message.contains("Rejected invalid"))
        assertTrue(TelemetryPresenter().decode(byteArrayOf(0x40, 0, 0x10, 0x0e)).message.contains("Rejected diagnostic"))
    }
    @Test fun `unavailable and absent metrics do not carry stale values`() {
        val p = TelemetryPresenter(); p.decode(byteArrayOf(0x40, 0, 0x10, 0x0e, 0xb4.toByte(), 0))
        val missing = p.decode(byteArrayOf(0, 0, 0x10, 0x0e)); assertNull(missing.cadence); assertNull(missing.power)
        // Total energy's documented sentinel is unavailable, not a displayed zero.
        val outcome = MeasurementReader.decode(UUID.fromString(INDOOR_BIKE_DATA), byteArrayOf(0, 1, 0x10, 0x0e, 0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte())) as MeasurementDecodeResult.Decoded
        assertNotEquals(0L, outcome.measurement.raw.unavailable)
    }
    @Test fun `more data remains a packet not an assembled record`() { assertTrue(TelemetryPresenter().decode(byteArrayOf(1, 0)).message.contains("More Data")) }
    @Test fun `resistance formats are explicit`() { assertEquals(ResistanceFormat.UINT8_WHOLE, selectedFormat(false).resistance); assertEquals(ResistanceFormat.SINT16_TENTHS, selectedFormat(true).resistance) }
    @Test fun `unsupported uuid and stale session are not accepted`() {
        assertTrue(MeasurementReader.decode(UUID.randomUUID(), byteArrayOf()) is MeasurementDecodeResult.Unsupported)
        val gate = SessionGate(); val first = gate.next(); gate.next(); assertFalse(gate.accepts(first)); assertTrue(gate.accepts(gate.current))
    }
    @Test fun `diagnostics replace rather than retain a valid display`() {
        for (bytes in listOf(byteArrayOf(0), byteArrayOf(0x40, 0, 0x10, 0x0e),
            byteArrayOf(0, 0, 0x10, 0x0e, 0), byteArrayOf(0, 0x20, 0x10, 0x0e))) {
            val p = TelemetryPresenter()
            p.decode(byteArrayOf(0, 0, 0x10, 0x0e))
            assertTrue(p.decode(bytes).message.startsWith("Rejected"))
            assertNull(p.state.speed)
        }
    }
    @Test fun `unsupported characteristic clears presenter values`() {
        val p = TelemetryPresenter()
        p.decode(byteArrayOf(0, 0, 0x10, 0x0e))
        assertEquals("Rejected unsupported characteristic", p.decode(byteArrayOf(), UUID(0, 0)).message)
        assertNull(p.state.speed)
    }
    @Test fun `explicit legacy width changes subsequent power alignment`() {
        // Resistance 10.0 (100 raw) in signed16 tenths, followed by power 200 W.
        val packet = byteArrayOf(0x60, 0, 0x10, 0x0e, 100, 0, 0xc8.toByte(), 0)
        assertTrue(TelemetryPresenter().decode(packet).message.startsWith("Rejected"))
        assertEquals("Power 200 W", TelemetryPresenter(selectedFormat(true)).decode(packet).power)
        assertEquals("Resistance 10.0", TelemetryPresenter(selectedFormat(true)).decode(packet).resistance)
        assertEquals("Resistance 100.0", TelemetryPresenter().decode(byteArrayOf(0x20, 0, 0x10, 0x0e, 100)).resistance)
    }
    @Test fun `more data does not retain mandatory speed from an earlier packet`() {
        val p = TelemetryPresenter()
        p.decode(byteArrayOf(0, 0, 0x10, 0x0e))
        assertNull(p.decode(byteArrayOf(1, 0)).speed)
    }
    @Test fun `permission selection covers both Android generations`() {
        assertArrayEquals(arrayOf("android.permission.ACCESS_FINE_LOCATION"), bluetoothPermissions(26))
        assertArrayEquals(bluetoothPermissions(26), bluetoothPermissions(30))
        assertArrayEquals(arrayOf("android.permission.BLUETOOTH_SCAN", "android.permission.BLUETOOTH_CONNECT"), bluetoothPermissions(31))
    }
}
