package io.github.deancochran.ftms.example.telemetry

import io.github.deancochran.ftms.measurement.MeasurementDecodeResult
import io.github.deancochran.ftms.measurement.MeasurementFormat
import io.github.deancochran.ftms.measurement.MeasurementReader
import io.github.deancochran.ftms.measurement.ResistanceFormat
import java.util.UUID
import java.util.Locale

const val INDOOR_BIKE_DATA: String = "00002ad2-0000-1000-8000-00805f9b34fb"

/** Pure application seam: each notification is a separate FTMS packet, never a synthetic record. */
class TelemetryPresenter(private val format: MeasurementFormat = MeasurementFormat()) {
    var state: TelemetryState = TelemetryState("Waiting for a packet")
        private set

    fun clear(message: String) { state = TelemetryState(message) }
    fun decode(bytes: ByteArray, uuid: UUID = UUID.fromString(INDOOR_BIKE_DATA), synthetic: Boolean = false): TelemetryState {
        when (val outcome = MeasurementReader.decode(uuid, bytes, format)) {
            is MeasurementDecodeResult.Decoded -> {
                val raw = outcome.measurement.raw
                if (raw.truncated || raw.trailingBytes || raw.reservedFlags) {
                    state = TelemetryState("Rejected diagnostic packet (truncated, trailing, or reserved flags)")
                } else {
                    state = TelemetryState(
                        if (synthetic) "Synthetic demo (no Bluetooth)" else if (raw.moreData) "Packet has More Data; displayed independently" else "Live packet (not an assembled record)",
                        outcome.measurement.speedMps?.let { "Speed %.2f m/s".format(Locale.ROOT, it) },
                        outcome.measurement.cadenceRpm?.let { "Cadence %.1f rpm".format(Locale.ROOT, it) },
                        outcome.measurement.powerWatts?.let { "Power %.0f W".format(Locale.ROOT, it) },
                        outcome.measurement.resistanceLevel?.let { "Resistance %.1f".format(Locale.ROOT, it) },
                    )
                }
            }
            is MeasurementDecodeResult.Invalid -> state = TelemetryState("Rejected invalid packet: ${outcome.error.message}")
            is MeasurementDecodeResult.Unsupported -> state = TelemetryState("Rejected unsupported characteristic")
        }
        return state
    }
}

data class TelemetryState(val message: String, val speed: String? = null, val cadence: String? = null, val power: String? = null, val resistance: String? = null) {
    fun text() = listOfNotNull(message, speed, cadence, power, resistance).joinToString("\n")
}

fun selectedFormat(signedTenths: Boolean) = MeasurementFormat(
    resistance = if (signedTenths) ResistanceFormat.SINT16_TENTHS else ResistanceFormat.UINT8_WHOLE,
)
