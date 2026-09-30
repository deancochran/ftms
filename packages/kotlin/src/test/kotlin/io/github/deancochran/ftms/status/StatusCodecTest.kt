package io.github.deancochran.ftms.status

import org.junit.jupiter.api.Assertions.assertArrayEquals
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class StatusCodecTest {
    @Test fun `machine encoder rejects operand overflow and incorrect arity`() {
        val cases = listOf(
            Triple(5, 2, intArrayOf(-1)), Triple(5, 2, intArrayOf(65536)),
            Triple(6, 3, intArrayOf(-32769)), Triple(7, 4, intArrayOf(32768)),
            Triple(9, 6, intArrayOf(256)), Triple(13, 12, intArrayOf(0x1000000)),
            Triple(15, 14, intArrayOf(1)), Triple(16, 15, intArrayOf(1, 2, 3, 4)),
            Triple(18, 17, intArrayOf(0, 0, -1, 0)), Triple(18, 17, intArrayOf(32768, 0, 0, 0)),
            Triple(5, 2, intArrayOf()), Triple(5, 2, intArrayOf(1, 2)),
        )
        for ((opcode, requestOpcode, operands) in cases) assertThrows(IllegalArgumentException::class.java) {
            StatusCodec.encodeMachine(MachineStatus(opcode, parameter = MachineStatusParameter(requestOpcode, operands)))
        }
        assertArrayEquals(byteArrayOf(18, 0, 0x80.toByte(), 0xff.toByte(), 0x7f, 0, 0xff.toByte()),
            StatusCodec.encodeMachine(MachineStatus(18, parameter = MachineStatusParameter(17, intArrayOf(-32768, 32767, 0, 255)))))
    }
    @Test fun `training encoder rejects unpaired surrogates without replacement`() {
        for (text in listOf("\uD800", "\uDC00", "x\uD800y")) assertThrows(IllegalArgumentException::class.java) {
            StatusCodec.encodeTraining(TrainingStatus(1, 1), text)
        }
        assertArrayEquals(byteArrayOf(1, 1, 0xf0.toByte(), 0x9f.toByte(), 0x9a.toByte(), 0xb2.toByte()),
            StatusCodec.encodeTraining(TrainingStatus(1, 1), "\uD83D\uDEB2"))
    }
    @Test fun `status inputs and returned arrays have independent ownership`() {
        val operands = intArrayOf(123)
        val parameter = MachineStatusParameter(2, operands)
        operands[0] = 0; parameter.operands[0] = 0
        assertEquals(123, parameter.operandAt(0))
        val text = byteArrayOf(65)
        val status = TrainingStatus(1, 1, text)
        text[0] = 0; status.text[0] = 0
        assertArrayEquals(byteArrayOf(65), status.text)
        val bytes = byteArrayOf(1, 1, 65)
        val decoded = StatusCodec.decodeTraining(bytes)
        bytes[2] = 0; decoded.text[0] = 0
        assertArrayEquals(byteArrayOf(65), decoded.text)
    }
    @Test fun `machine target resistance keeps signed raw tenths`() {
        val bytes = byteArrayOf(7, 0x85.toByte(), 0xff.toByte())
        val decoded = StatusCodec.decodeMachine(bytes)
        assertEquals(4, decoded.parameter!!.requestOpcode)
        assertEquals(-123, decoded.parameter.operandAt(0))
        assertArrayEquals(bytes, StatusCodec.encodeMachine(MachineStatus(7, parameter = MachineStatusParameter(4, intArrayOf(-123)))))
    }
    @Test fun `machine partial and unknown statuses retain exact diagnostics`() {
        val empty = StatusCodec.decodeMachine(ByteArray(0)); assertEquals(true, empty.unknownOpcode); assertEquals(true, empty.truncated)
        val unknown = StatusCodec.decodeMachine(byteArrayOf(0x7f)); assertEquals(true, unknown.unknownOpcode)
        assertThrows(IllegalArgumentException::class.java) { StatusCodec.encodeMachine(unknown) }
    }
    @Test fun `training status retains malformed UTF8 but encoder rejects diagnostics`() {
        val decoded = StatusCodec.decodeTraining(byteArrayOf(3, 2, 0xc3.toByte(), 0x28))
        assertEquals(true, decoded.textPresent); assertEquals(true, decoded.extendedString); assertEquals(true, decoded.invalidUtf8)
        assertThrows(IllegalArgumentException::class.java) { StatusCodec.encodeTraining(decoded, "ok") }
        assertArrayEquals(byteArrayOf(3, 2, 'o'.code.toByte(), 'k'.code.toByte()), StatusCodec.encodeTraining(TrainingStatus(3, 2), "ok"))
    }
}
