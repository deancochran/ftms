package io.github.deancochran.ftms.status

import com.google.gson.JsonNull
import com.google.gson.JsonObject
import io.github.deancochran.ftms.measurement.RawCorpusSupport
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class StatusCorpusTest {
    private fun machineJson(value: MachineStatus): JsonObject = JsonObject().apply {
        addProperty("opcode", value.opcode); addProperty("action", value.action)
        add("parameter", value.parameter?.let { p -> JsonObject().apply {
            addProperty("opcode", p.requestOpcode); add("operands", RawCorpusSupport.array(p.operands))
        } } ?: JsonNull.INSTANCE)
        addProperty("unknownOpcode", RawCorpusSupport.flag(value.unknownOpcode))
        addProperty("reservedValue", RawCorpusSupport.flag(value.reservedValue))
        addProperty("truncated", RawCorpusSupport.flag(value.truncated))
        addProperty("trailingBytes", RawCorpusSupport.flag(value.trailingBytes))
    }
    private fun trainingJson(value: TrainingStatus): JsonObject = JsonObject().apply {
        addProperty("flags", value.flags); addProperty("code", value.code)
        addProperty("textOffset", value.textOffset); addProperty("textSize", value.textSize)
        addProperty("textPresent", RawCorpusSupport.flag(value.textPresent))
        addProperty("extendedString", RawCorpusSupport.flag(value.extendedString))
        addProperty("reservedFlags", value.reservedFlags)
        addProperty("reservedValue", RawCorpusSupport.flag(value.reservedValue))
        addProperty("invalidFlags", RawCorpusSupport.flag(value.invalidFlags))
        addProperty("invalidUtf8", RawCorpusSupport.flag(value.invalidUtf8))
        addProperty("truncated", RawCorpusSupport.flag(value.truncated))
        addProperty("trailingBytes", RawCorpusSupport.flag(value.trailingBytes))
        addProperty("textHex", value.text.joinToString("") { "%02x".format(it.toInt() and 255) })
    }
    @Test fun `canonical statuses all declared directions`() {
        val base = "shared/conformance/statuses"
        RawCorpusSupport.identity("$base/v1/schema.json", "$base/v1/vectors.json", "$base/README.md")
        val corpus = RawCorpusSupport.load("$base/v1/vectors.json")
        RawCorpusSupport.validate("$base/v1/schema.json", corpus)
        assertEquals(1, corpus["schemaVersion"].asInt)
        val accounting = RawCorpusSupport.Accounting("statuses")
        for ((category, count) in listOf("machine" to 28, "training" to 10)) {
            assertEquals(count, corpus[category].asJsonArray.size())
            for (element in corpus[category].asJsonArray) {
                val case = element.asJsonObject
                val id = case["id"].asString
                assertEquals(category, case["operation"].asString)
                val bytes = RawCorpusSupport.bytes(case["bytes"])
                val expected = case["decoded"].asJsonObject
                accounting.case(id, category)
                accounting.direction(id, "decode") {
                    val actual = if (category == "machine") machineJson(StatusCodec.decodeMachine(bytes))
                        else trainingJson(StatusCodec.decodeTraining(bytes))
                    RawCorpusSupport.exact(expected, actual)
                }
                if (case["encode"].asBoolean) accounting.direction(id, "encode") {
                    val encoded = if (category == "machine") {
                        val parameter = expected["parameter"].takeUnless { it.isJsonNull }?.asJsonObject?.let {
                            MachineStatusParameter(it["opcode"].asInt, RawCorpusSupport.ints(it["operands"]))
                        }
                        StatusCodec.encodeMachine(MachineStatus(expected["opcode"].asInt, expected["action"].asInt, parameter))
                    } else {
                        val text = expected["textHex"].asString.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
                        StatusCodec.encodeTraining(TrainingStatus(expected["flags"].asInt, expected["code"].asInt), text.toString(Charsets.UTF_8))
                    }
                    assertArrayEquals(bytes, encoded)
                }
            }
        }
        accounting.finish(38, 63)
    }
}
