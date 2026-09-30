package io.github.deancochran.ftms.foundation

import com.google.gson.JsonParser
import io.github.deancochran.ftms.*
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import kotlin.test.*

internal class FoundationBoundaryTest {
    @TestFactory fun semanticCommands(): List<DynamicTest> {
        // Independently authored semantic operands; bytes come directly from the canonical corpus.
        val commands = listOf(
            ControlCommand.RequestControl, ControlCommand.Reset, ControlCommand.TargetSpeed(1234),
            ControlCommand.TargetInclination(-123), ControlCommand.TargetResistance(-10),
            ControlCommand.TargetPower(250), ControlCommand.TargetHeartRate(180), ControlCommand.StartResume,
            ControlCommand.StopPause(StopPauseAction.STOP), ControlCommand.TargetEnergy(600),
            ControlCommand.TargetSteps(42), ControlCommand.TargetStrides(43), ControlCommand.TargetDistance(65536),
            ControlCommand.TargetTrainingTime(3600), ControlCommand.TwoZoneTime(1, 2),
            ControlCommand.ThreeZoneTime(1, 2, 3), ControlCommand.FiveZoneTime(1, 2, 3, 4, 5),
            ControlCommand.IndoorBikeSimulation(-100, 125, 3, 4), ControlCommand.WheelCircumference(2100),
            ControlCommand.SpinDown(SpinDownAction.IGNORE), ControlCommand.TargetCadence(120)
        )
        val document = Corpus.read("shared/conformance/controls/v1/vectors.json")
        Corpus.validate(Corpus.read("shared/conformance/controls/v1/schema.json"), document)
        val requests = document.getAsJsonArray("requests").map { it.asJsonObject }.associateBy { it["id"].asString }
        return commands.flatMapIndexed { opcode, command ->
            val id = "request-opcode-${opcode.toString().padStart(2, '0')}"
            val bytes = Corpus.bytes(requests.getValue(id)["bytes"])
            listOf(
                DynamicTest.dynamicTest("$id semantic encode") { assertContentEquals(bytes, ControlCodec.encodeCommand(command)) },
                DynamicTest.dynamicTest("$id semantic decode") { assertEquals(command, ControlCodec.decodeCommand(bytes)) }
            )
        }
    }

    private fun rejects(error: FtmsError, action: () -> Unit) {
        assertEquals(error, assertFailsWith<FtmsException>(block = action).error)
    }

    @Test fun featureWidthsAndLengths() {
        listOf(-1L, 0x100000000L).forEach { invalid ->
            rejects(FtmsError.RANGE) { Features(invalid, 0) }
            rejects(FtmsError.RANGE) { Features(0, invalid) }
        }
        listOf(0, 7, 9).forEach { rejects(FtmsError.LENGTH) { FeatureCodec.decode(ByteArray(it)) } }
    }

    @Test fun rangeEncodingRejectsInvalidRawValues() {
        val valid = SupportedRange(RangeKind.POWER, -100, 4000, 5, 1, RangeUnit.WATTS)
        val invalid = listOf(
            SupportedRange(valid.kind, -32769, 4000, 5, 1, valid.unit),
            SupportedRange(valid.kind, -100, 32768, 5, 1, valid.unit),
            SupportedRange(valid.kind, 100, 99, 5, 1, valid.unit),
            SupportedRange(valid.kind, -100, 4000, 0, 1, valid.unit),
            SupportedRange(valid.kind, -100, 4000, 65536, 1, valid.unit),
            SupportedRange(valid.kind, -100, 4000, 5, 10, valid.unit),
            SupportedRange(valid.kind, -100, 4000, 5, 1, RangeUnit.LEVEL),
            SupportedRange(RangeKind.SPEED, -1, 100, 1, 100, RangeUnit.KILOMETRES_PER_HOUR),
            SupportedRange(RangeKind.SPEED, 0, 65536, 1, 100, RangeUnit.KILOMETRES_PER_HOUR),
            SupportedRange(RangeKind.RESISTANCE, 0, 256, 1, 1, RangeUnit.LEVEL),
            SupportedRange(RangeKind.HEART_RATE, 0, 255, 256, 1, RangeUnit.BEATS_PER_MINUTE)
        )
        invalid.forEach { rejects(FtmsError.RANGE) { RangeCodec.encode(it) } }
        rejects(FtmsError.KIND) { RangeCodec.encode(valid, ResistanceRangeFormat.SINT16_TENTHS) }
        rejects(FtmsError.KIND) { RangeCodec.decode(RangeKind.POWER, ByteArray(6), ResistanceRangeFormat.SINT16_TENTHS) }
        rejects(FtmsError.KIND) { RangeCodec.inspect(RangeKind.POWER, ByteArray(6), ResistanceRangeFormat.SINT16_TENTHS) }
        val signed = SupportedRange(RangeKind.RESISTANCE, -32768, 32767, 65535, 10, RangeUnit.LEVEL)
        assertContentEquals(byteArrayOf(0, -128, -1, 127, -1, -1), RangeCodec.encode(signed, ResistanceRangeFormat.SINT16_TENTHS))
    }

    @Test fun controlsRejectWidthsAndMalformedOperands() {
        listOf(
            2 to longArrayOf(-1), 2 to longArrayOf(65536), 3 to longArrayOf(-32769),
            4 to longArrayOf(32768), 5 to longArrayOf(32768), 6 to longArrayOf(256),
            8 to longArrayOf(0), 12 to longArrayOf(0x1000000), 19 to longArrayOf(3),
            17 to longArrayOf(0, 0, -1, 0), 17 to longArrayOf(0, 0, 0, 256)
        ).forEach { (opcode, operands) -> rejects(FtmsError.RANGE) { ControlCodec.encodeRequest(ControlRequest(opcode, operands)) } }
        rejects(FtmsError.LENGTH) { ControlCodec.encodeRequest(ControlRequest(16, longArrayOf(1, 2))) }
        rejects(FtmsError.LENGTH) { ControlCodec.encodeRequest(ControlRequest(0, longArrayOf(1))) }
        rejects(FtmsError.RANGE) { ControlCodec.encodeCommand(ControlCommand.TargetResistance(-1), ResistanceControlFormat.UINT8_TENTHS) }
        assertContentEquals(byteArrayOf(4, -1), ControlCodec.encodeCommand(ControlCommand.TargetResistance(255), ResistanceControlFormat.UINT8_TENTHS))
        assertEquals(ControlCommand.TargetResistance(255), ControlCodec.decodeCommand(byteArrayOf(4, -1), ResistanceControlFormat.UINT8_TENTHS))
        assertContentEquals(byteArrayOf(12, -1, -1, -1), ControlCodec.encodeCommand(ControlCommand.TargetDistance(0xffffff)))
    }

    @Test fun responsesRejectNonCanonicalEncodingButRetainDecodeEvidence() {
        listOf(
            ControlResponse(2, 99, 0, 0, 0, 0, 1, 0),
            ControlResponse(2, 1, 0, 0, 0, 0, 0, 1),
            ControlResponse(2, 1, 1, 100, 200, 0, 0, 0),
            ControlResponse(19, 2, 1, 100, 200, 0, 0, 0),
            ControlResponse(19, 1, 0, 1, 0, 0, 0, 0),
            ControlResponse(250, 2, 0, 0, 0, 0, 0, 0),
            ControlResponse(19, 1, 1, -1, 200, 0, 0, 0),
            ControlResponse(19, 1, 1, 100, 65536, 0, 0, 0)
        ).forEach { rejects(FtmsError.RANGE) { ControlCodec.encodeResponse(it) } }
        rejects(FtmsError.KIND) { ControlCodec.encodeResponse(ControlResponse(250, 1, 0, 0, 0, 1, 0, 0)) }
        assertContentEquals(byteArrayOf(-128, 19, 1), ControlCodec.encodeResponse(ControlResponse(19, 1, 0, 0, 0, 0, 0, 0)))
        assertEquals(0, ControlCodec.decodeResponse(byteArrayOf(-128, 19, 1)).parameter)
        for (length in listOf(4, 5, 6, 8)) rejects(FtmsError.LENGTH) {
            ControlCodec.decodeResponse(ByteArray(length).apply { this[0] = -128; this[1] = 19; this[2] = 1 })
        }
    }

    @Test fun publicValuesAreDefensive() {
        val operands = longArrayOf(123)
        val request = ControlRequest(2, operands)
        operands[0] = 999
        request.operands()[0] = 888
        assertContentEquals(longArrayOf(123), request.operands())
        val candidates = mutableListOf(RangeCandidate(RangeProfile.UINT8_WHOLE, 3, InspectionStatus.LENGTH, null))
        val inspection = RangeInspection(RangeProfile.UINT8_WHOLE, 0, 3, InspectionStatus.LENGTH, null, candidates)
        candidates.clear()
        assertEquals(1, inspection.candidates.size)
        assertFailsWith<UnsupportedOperationException> { (inspection.candidates as MutableList).clear() }
    }

    @Test fun strictHarnessRejectsBadSchemaAndComparisonInputs() {
        val schema = Corpus.read("shared/conformance/values/v1/schema.json")
        val fixtures = Corpus.read("shared/conformance/values/v1/vectors.json")
        val malformed = fixtures.deepCopy().apply { addProperty("unknown", true) }
        assertFailsWith<IllegalStateException> { Corpus.validate(schema, malformed) }
        val invalidByte = fixtures.deepCopy().apply { getAsJsonArray("cases")[0].asJsonObject.getAsJsonArray("expectedBytes").set(0, Corpus.json(256)) }
        assertFailsWith<IllegalStateException> { Corpus.validate(schema, invalidByte) }
        val cases = fixtures.getAsJsonArray("cases").map { it.asJsonObject }
        assertFailsWith<IllegalStateException> { Corpus.unique(cases + cases.first()) }
        listOf("1" to "1.0", "1" to "\"1\"", "null" to "0", "{}" to "{\"extra\":0}",
            "[1,2]" to "[2,1]", "[1]" to "[1,2]", "{\"x\":null}" to "{}").forEach { (expected, actual) ->
            assertFailsWith<IllegalStateException> { Corpus.exact(JsonParser.parseString(expected), JsonParser.parseString(actual)) }
        }
    }
}
