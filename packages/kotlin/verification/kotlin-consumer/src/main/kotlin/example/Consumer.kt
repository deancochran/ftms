package example

import io.github.deancochran.ftms.FeatureCodec
import io.github.deancochran.ftms.Features
import io.github.deancochran.ftms.measurement.MeasurementDecodeResult
import io.github.deancochran.ftms.measurement.MeasurementReader
import java.util.UUID

fun main() {
    val literal = byteArrayOf(-1, -1, -1, -1, 0, 0, 0, -128)
    val value = FeatureCodec.decode(literal)
    check(value.machine == 0xffffffffL && value.target == 0x80000000L)
    check(FeatureCodec.encode(Features(0xffffffffL, 0x80000000L)).contentEquals(literal))
    val reading = MeasurementReader.decode(UUID.fromString("00002ad2-0000-1000-8000-00805f9b34fb"), byteArrayOf(0, 0, 16, 14))
    check((reading as? MeasurementDecodeResult.Decoded)?.measurement?.speedMps == 10.0)
    check(runCatching { FeatureCodec.decode(byteArrayOf()) }.exceptionOrNull() is IllegalArgumentException)
    println("Kotlin isolated artifact consumer passed")
}
