package io.github.deancochran.ftms.status

import org.junit.jupiter.api.Assertions.assertArrayEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class MachineStatusActionTest {
    @Test fun `training flags cannot overflow the wire byte`() {
        for (flags in listOf(-256, 256, 257, 65536, Int.MIN_VALUE, Int.MAX_VALUE)) {
            assertThrows(IllegalArgumentException::class.java) {
                StatusCodec.encodeTraining(TrainingStatus(flags, 0))
            }
        }
    }
    @Test fun `non-action statuses reject action state instead of losing it`() {
        val lengths = mapOf(1 to 1, 3 to 1, 4 to 1, 255 to 1, 5 to 3, 6 to 3,
            7 to 3, 8 to 3, 9 to 2, 10 to 3, 11 to 3, 12 to 3, 13 to 4,
            14 to 3, 15 to 5, 16 to 7, 17 to 11, 18 to 7, 19 to 3, 21 to 3)
        for ((opcode, length) in lengths) {
            val literal = ByteArray(length).also { it[0] = opcode.toByte() }
            val canonical = StatusCodec.decodeMachine(literal)
            assertArrayEquals(literal, StatusCodec.encodeMachine(canonical))
            for (action in listOf(-1, 1, 255, 256, Int.MIN_VALUE, Int.MAX_VALUE)) {
                assertThrows(IllegalArgumentException::class.java) {
                    StatusCodec.encodeMachine(MachineStatus(opcode, action, canonical.parameter))
                }
            }
        }
    }
}
