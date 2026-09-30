package io.github.deancochran.ftms.measurement

/** Raw FTMS measurement values retain their on-wire units and integer widths. */
public enum class MeasurementKind { TREADMILL, CROSS_TRAINER, STEP_CLIMBER, STAIR_CLIMBER, ROWER, INDOOR_BIKE }
public enum class ResistanceFormat { UINT8_WHOLE, SINT16_TENTHS }
public enum class TreadmillPaceFormat { UINT16, UINT8_LEGACY }
public data class MeasurementFormat @JvmOverloads constructor(
    public val resistance: ResistanceFormat = ResistanceFormat.UINT8_WHOLE,
    public val treadmillPace: TreadmillPaceFormat = TreadmillPaceFormat.UINT16,
)

/** Field indexes are the stable 30-column raw conformance field order. */
public object MeasurementField {
    public const val SPEED: Int = 0; public const val AVERAGE_SPEED: Int = 1; public const val DISTANCE: Int = 2
    public const val INCLINATION: Int = 3; public const val RAMP_ANGLE: Int = 4; public const val POSITIVE_ELEVATION: Int = 5
    public const val NEGATIVE_ELEVATION: Int = 6; public const val INSTANTANEOUS_PACE: Int = 7; public const val AVERAGE_PACE: Int = 8
    public const val TOTAL_ENERGY: Int = 9; public const val ENERGY_PER_HOUR: Int = 10; public const val ENERGY_PER_MINUTE: Int = 11
    public const val HEART_RATE: Int = 12; public const val MET: Int = 13; public const val ELAPSED_TIME: Int = 14
    public const val REMAINING_TIME: Int = 15; public const val FORCE_ON_BELT: Int = 16; public const val POWER: Int = 17
    public const val STEP_RATE: Int = 18; public const val AVERAGE_STEP_RATE: Int = 19; public const val STRIDE_COUNT: Int = 20
    public const val RESISTANCE: Int = 21; public const val AVERAGE_POWER: Int = 22; public const val FLOOR_COUNT: Int = 23
    public const val STEP_COUNT: Int = 24; public const val STROKE_RATE: Int = 25; public const val STROKE_COUNT: Int = 26
    public const val AVERAGE_STROKE_RATE: Int = 27; public const val CADENCE: Int = 28; public const val AVERAGE_CADENCE: Int = 29
    public const val COUNT: Int = 30
}

/** Immutable decoded or encoder-input measurement evidence. */
public class Measurement @JvmOverloads constructor(
    public val kind: MeasurementKind,
    public val flags: Int,
    public val present: Long,
    public val unavailable: Long,
    values: IntArray,
    public val moreData: Boolean = false,
    public val backward: Boolean = false,
    public val truncated: Boolean = false,
    public val trailingBytes: Boolean = false,
    public val reservedFlags: Boolean = false,
    public val bytesRead: Int = 0,
) {
    private val rawValues: IntArray = values.copyOf().also { require(it.size == MeasurementField.COUNT) }
    public val values: IntArray get() = rawValues.copyOf()
    public fun valueAt(field: Int): Int { require(field in 0 until MeasurementField.COUNT); return rawValues[field] }
}

private data class Field(val bit: Int, val width: Int, val index: Int, val signed: Boolean, val unavailable: Boolean)
private data class Layout(val flagBytes: Int, val valid: Int, val fields: Array<Field>)

/** Stateless bidirectional codec. It neither reassembles More Data fragments nor performs transport I/O. */
public object MeasurementCodec {
    private fun f(b: Int, w: Int, i: Int, s: Boolean = false, u: Boolean = false) = Field(b, w, i, s, u)
    private val layouts = arrayOf(
        Layout(2, 0x1fff, arrayOf(f(0,2,0),f(1,2,1),f(2,3,2),f(3,2,3,true,true),f(3,2,4,true,true),f(4,2,5),f(4,2,6),f(5,2,7),f(6,2,8),f(7,2,9,false,true),f(7,2,10,false,true),f(7,1,11,false,true),f(8,1,12),f(9,1,13),f(10,2,14),f(11,2,15),f(12,2,16,true,true),f(12,2,17,true,true))),
        Layout(3, 0xffff, arrayOf(f(0,2,0),f(1,2,1),f(2,3,2),f(3,2,18,false,true),f(3,2,19,false,true),f(4,2,20),f(5,2,5),f(5,2,6),f(6,2,3,true,true),f(6,2,4,true,true),f(7,1,21),f(8,2,17,true),f(9,2,22,true),f(10,2,9,false,true),f(10,2,10,false,true),f(10,1,11,false,true),f(11,1,12),f(12,1,13),f(13,2,14),f(14,2,15))),
        Layout(2, 0x01ff, arrayOf(f(0,2,23),f(0,2,24),f(1,2,18),f(2,2,19),f(3,2,5),f(4,2,9,false,true),f(4,2,10,false,true),f(4,1,11,false,true),f(5,1,12),f(6,1,13),f(7,2,14),f(8,2,15))),
        Layout(2, 0x03ff, arrayOf(f(0,2,23),f(1,2,18),f(2,2,19),f(3,2,5),f(4,2,20),f(5,2,9,false,true),f(5,2,10,false,true),f(5,1,11,false,true),f(6,1,12),f(7,1,13),f(8,2,14),f(9,2,15))),
        Layout(2, 0x1fff, arrayOf(f(0,1,25),f(0,2,26),f(1,1,27),f(2,3,2),f(3,2,7),f(4,2,8),f(5,2,17,true),f(6,2,22,true),f(7,1,21),f(8,2,9,false,true),f(8,2,10,false,true),f(8,1,11,false,true),f(9,1,12),f(10,1,13),f(11,2,14),f(12,2,15))),
        Layout(2, 0x1fff, arrayOf(f(0,2,0),f(1,2,1),f(2,2,28),f(3,2,29),f(4,3,2),f(5,1,21),f(6,2,17,true),f(7,2,22,true),f(8,2,9,false,true),f(8,2,10,false,true),f(8,1,11,false,true),f(9,1,12),f(10,1,13),f(11,2,14),f(12,2,15)))
    )
    private fun changed(kind: MeasurementKind, field: Field, format: MeasurementFormat): Field = when {
        field.index == 21 && kind in arrayOf(MeasurementKind.CROSS_TRAINER, MeasurementKind.ROWER, MeasurementKind.INDOOR_BIKE) && format.resistance == ResistanceFormat.SINT16_TENTHS -> field.copy(width = 2, signed = true)
        kind == MeasurementKind.TREADMILL && field.index in 7..8 && format.treadmillPace == TreadmillPaceFormat.UINT8_LEGACY -> field.copy(width = 1)
        else -> field
    }
    private fun selected(flags: Int, field: Field): Boolean = if (field.bit == 0) flags and 1 == 0 else flags and (1 shl field.bit) != 0
    private fun read(bytes: ByteArray, at: Int, width: Int): Int { var v=0; repeat(width) { v = v or ((bytes[at + it].toInt() and 255) shl (8 * it)) }; return v }
    private fun put(out: MutableList<Byte>, value: Int, width: Int) { repeat(width) { out += ((value ushr (8 * it)) and 255).toByte() } }
    private fun sentinel(field: Field): Int = if (field.signed) 0x7fff else if (field.width == 1) 0xff else 0xffff

    @JvmStatic @JvmOverloads public fun decode(kind: MeasurementKind, bytes: ByteArray, format: MeasurementFormat = MeasurementFormat()): Measurement {
        val layout = layouts[kind.ordinal]; require(bytes.size >= layout.flagBytes) { "measurement flags truncated" }
        val flags = read(bytes, 0, layout.flagBytes); val values = IntArray(MeasurementField.COUNT); var present=0L; var unavailable=0L; var offset=layout.flagBytes
        for (original in layout.fields) { val field=changed(kind, original, format); if (!selected(flags, field)) continue
            if (offset + field.width > bytes.size) return Measurement(kind,flags,present,unavailable,values,flags and 1 != 0,kind == MeasurementKind.CROSS_TRAINER && flags and 0x8000 != 0,true,false,(flags and layout.valid.inv()) != 0,offset)
            val raw=read(bytes,offset,field.width); offset += field.width; present = present or (1L shl field.index)
            if (field.unavailable && raw == sentinel(field)) unavailable = unavailable or (1L shl field.index)
            else values[field.index] = if (field.signed && raw > 0x7fff) raw - 0x10000 else raw
        }
        return Measurement(kind,flags,present,unavailable,values,flags and 1 != 0,kind == MeasurementKind.CROSS_TRAINER && flags and 0x8000 != 0,false,offset < bytes.size,(flags and layout.valid.inv()) != 0,offset)
    }

    @JvmStatic @JvmOverloads public fun encode(measurement: Measurement, format: MeasurementFormat = MeasurementFormat()): ByteArray {
        val layout=layouts[measurement.kind.ordinal]
        require(!measurement.truncated && !measurement.trailingBytes && !measurement.reservedFlags) { "diagnostic measurement cannot encode" }
        require((measurement.flags and layout.valid.inv()) == 0) { "reserved measurement flags" }; require(measurement.unavailable and measurement.present == measurement.unavailable) { "unavailable field not present" }
        var required=0L; for (field in layout.fields) if (selected(measurement.flags,field)) required = required or (1L shl field.index)
        require(measurement.present == required) { "measurement present mask does not match flags" }
        val out=ArrayList<Byte>(); put(out,measurement.flags,layout.flagBytes)
        for (original in layout.fields) { val field=changed(measurement.kind,original,format); if (!selected(measurement.flags,field)) continue; val bit=1L shl field.index; val value=measurement.valueAt(field.index)
            if (measurement.unavailable and bit != 0L) { require(field.unavailable) { "field has no unavailable sentinel" }; put(out,sentinel(field),field.width) }
            else { val max=if(field.width==1)255 else if(field.width==2)65535 else 0xffffff; require(if(field.signed) value in -32768..32767 else value >= 0 && value <= max) { "measurement value outside wire range" }; require(!field.unavailable || value != sentinel(field)) { "sentinel requires unavailable mask" }; put(out,value,field.width) }
        }
        return out.toByteArray()
    }
}
