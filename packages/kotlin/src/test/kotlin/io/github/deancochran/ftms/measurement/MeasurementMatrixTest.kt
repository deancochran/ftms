package io.github.deancochran.ftms.measurement

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class MeasurementMatrixTest {
    private data class Field(val bit: Int, val width: Int, val index: Int, val signed: Boolean, val sentinel: Boolean)
    private data class Golden(val bytes: ByteArray, val measurement: Measurement)

    @Test fun `all canonical structural configurations sentinel RFU and incomplete prefixes`() {
        val base = "shared/conformance/measurement-matrix/v1"
        RawCorpusSupport.identity("$base/layouts.json", "$base/README.md")
        val matrix = RawCorpusSupport.load("$base/layouts.json")
        assertEquals("ftms-measurement-matrix-v1", matrix["contract"].asString)
        var structures = 0
        var sentinels = 0
        var reserved = 0
        var prefixes = 0
        var configurations = 0
        val perKind = IntArray(6)
        for (element in matrix["layouts"].asJsonArray) {
            val layout = element.asJsonObject
            val kind = layout["kind"].asInt
            val flagBytes = layout["flagBytes"].asInt
            val groups = layout["optionalGroups"].asInt
            for (variant in 0 until if (kind in listOf(0, 1, 4, 5)) 2 else 1) {
                configurations++
                val format = MeasurementFormat(
                    resistance = if (variant == 1 && kind != 0) ResistanceFormat.SINT16_TENTHS else ResistanceFormat.UINT8_WHOLE,
                    treadmillPace = if (variant == 1 && kind == 0) TreadmillPaceFormat.UINT8_LEGACY else TreadmillPaceFormat.UINT16,
                )
                val fields = layout["fields"].asJsonArray.map {
                    val f = RawCorpusSupport.ints(it)
                    Field(f[0], when {
                        variant == 1 && f[2] == 21 -> 2
                        variant == 1 && kind == 0 && f[2] in 7..8 -> 1
                        else -> f[1]
                    }, f[2], f[3] == 1 || (variant == 1 && f[2] == 21), f[4] == 1)
                }
                fun build(flags: Int, sentinelField: Int = -1, prefix: Int = Int.MAX_VALUE, rfu: Boolean = false): Golden {
                    val bytes = ArrayList<Byte>()
                    repeat(flagBytes) { bytes.add((flags ushr (it * 8)).toByte()) }
                    val values = IntArray(30)
                    var present = 0L
                    var unavailable = 0L
                    var truncated = false
                    for (f in fields) {
                        if (if (f.bit == 0) flags and 1 != 0 else flags and (1 shl f.bit) == 0) continue
                        if (bytes.size + f.width > prefix) { truncated = true; break }
                        val sentinel = f.index == sentinelField
                        val value = if (sentinel) {
                            if (f.signed) 32767 else (1 shl (8 * f.width)) - 1
                        } else (f.index + 1) * if (f.signed) -1 else 1
                        values[f.index] = if (sentinel) 0 else value
                        present = present or (1L shl f.index)
                        if (sentinel) unavailable = unavailable or (1L shl f.index)
                        repeat(f.width) { bytes.add((value ushr (it * 8)).toByte()) }
                    }
                    return Golden(bytes.toByteArray(), Measurement(MeasurementKind.entries[kind], flags, present,
                        unavailable, values, flags and 1 != 0, kind == 1 && flags and 0x8000 != 0,
                        truncated, false, rfu, bytes.size))
                }
                fun check(flags: Int, sentinelField: Int = -1) {
                    val golden = build(flags, sentinelField)
                    val label = "kind=$kind variant=$variant flags=$flags sentinel=$sentinelField"
                    RawCorpusSupport.exact(RawCorpusSupport.measurementJson(golden.measurement),
                        RawCorpusSupport.measurementJson(MeasurementCodec.decode(MeasurementKind.entries[kind], golden.bytes, format)), label)
                    assertArrayEquals(golden.bytes, MeasurementCodec.encode(golden.measurement, format), label)
                }
                for (subset in 0 until (1 shl groups)) for (more in 0..1) for (backward in 0 until if (kind == 1) 2 else 1) {
                    check((subset shl 1) or more or (backward shl 15))
                    structures++; perKind[kind]++
                }
                val all = ((1 shl groups) - 1) shl 1
                for (field in fields.filter { it.sentinel }) { check(all, field.index); sentinels++ }
                val full = build(all)
                assertEquals(layout["fullLength"].asInt + if (variant == 1) { if (kind == 0) -2 else 1 } else 0, full.bytes.size)
                for (length in full.bytes.indices) {
                    val bytes = full.bytes.copyOf(length)
                    if (length < flagBytes) assertThrows(IllegalArgumentException::class.java) {
                        MeasurementCodec.decode(MeasurementKind.entries[kind], bytes, format)
                    } else {
                        val expected = build(all, prefix = length).measurement
                        RawCorpusSupport.exact(RawCorpusSupport.measurementJson(expected),
                            RawCorpusSupport.measurementJson(MeasurementCodec.decode(MeasurementKind.entries[kind], bytes, format)),
                            "prefix kind=$kind variant=$variant length=$length")
                    }
                    prefixes++
                }
                for (bit in (if (kind == 1) 16 else groups + 1) until flagBytes * 8) {
                    val flags = all or (1 shl bit)
                    val golden = build(flags, rfu = true)
                    RawCorpusSupport.exact(RawCorpusSupport.measurementJson(golden.measurement),
                        RawCorpusSupport.measurementJson(MeasurementCodec.decode(MeasurementKind.entries[kind], golden.bytes, format)))
                    // Reject authoritative RFU bits even if caller did not set diagnostic metadata.
                    assertThrows(IllegalArgumentException::class.java) { MeasurementCodec.encode(build(flags).measurement, format) }
                    reserved++
                }
            }
        }
        assertEquals(181760, structures)
        assertArrayEquals(intArrayOf(16384, 131072, 512, 1024, 16384, 16384), perKind)
        assertEquals(46, sentinels); assertEquals(47, reserved); assertEquals(10, configurations)
        assertEquals(315, prefixes)
        println("measurement-matrix contract=ftms-measurement-matrix-v1 structures=$structures decode=$structures encode=$structures perKind=${perKind.contentToString()} sentinel=$sentinels RFU=$reserved configurations=$configurations prefixes=$prefixes failed=0 unsupported=0 skipped=0")
    }
}
