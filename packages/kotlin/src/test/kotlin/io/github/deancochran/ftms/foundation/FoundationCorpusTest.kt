package io.github.deancochran.ftms.foundation

import com.google.gson.JsonElement
import com.google.gson.JsonNull
import com.google.gson.JsonObject
import io.github.deancochran.ftms.*
import org.junit.jupiter.api.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

internal class FoundationCorpusTest {
    private fun JsonObject.int(key: String) = get(key).asInt
    private fun JsonObject.cases(key: String) = getAsJsonArray(key).map { it.asJsonObject }
    private fun kind(name: String) = when (name) {
        "speed" -> RangeKind.SPEED
        "inclination" -> RangeKind.INCLINATION
        "resistance" -> RangeKind.RESISTANCE
        "heartRate" -> RangeKind.HEART_RATE
        "power" -> RangeKind.POWER
        else -> error("Unknown range kind $name")
    }
    private fun kind(value: RangeKind) = when (value) {
        RangeKind.SPEED -> "speed"
        RangeKind.INCLINATION -> "inclination"
        RangeKind.RESISTANCE -> "resistance"
        RangeKind.HEART_RATE -> "heartRate"
        RangeKind.POWER -> "power"
    }
    private fun profile(value: RangeProfile) = when (value) {
        RangeProfile.UINT16_HUNDREDTHS -> "uint16Hundredths"
        RangeProfile.SINT16_TENTHS -> "signed16Tenths"
        RangeProfile.UINT8_WHOLE -> "uint8Whole"
        RangeProfile.UINT8_BPM -> "uint8Bpm"
        RangeProfile.SINT16_WATTS -> "signed16Watts"
    }
    private fun rawRange(value: SupportedRange?): JsonElement = if (value == null) JsonNull.INSTANCE else Corpus.json(mapOf(
        "kind" to kind(value.kind), "minimum" to value.minimum, "maximum" to value.maximum,
        "increment" to value.increment, "scaleDivisor" to value.scaleDivisor, "unit" to value.unit.wire))
    private fun range(value: JsonObject) = SupportedRange(kind(value["kind"].asString), value.int("minimum"),
        value.int("maximum"), value.int("increment"), value.int("scaleDivisor"), RangeUnit.entries.single { it.wire == value.int("unit") })
    private fun wire(bytes: ByteArray) = Corpus.json(bytes.map { it.toInt() and 255 })
    private fun rawResponse(value: ControlResponse) = Corpus.json(mapOf("requestOpcode" to value.requestOpcode,
        "resultCode" to value.resultCode, "parameter" to value.parameter, "low" to value.low, "high" to value.high,
        "unknownRequest" to value.unknownRequest, "unknownResult" to value.unknownResult, "unexpectedParameters" to value.unexpectedParameters))
    private fun response(value: JsonObject) = ControlResponse(value.int("requestOpcode"), value.int("resultCode"),
        value.int("parameter"), value.int("low"), value.int("high"), value.int("unknownRequest"),
        value.int("unknownResult"), value.int("unexpectedParameters"))
    private fun format(value: JsonObject) = when (value["format"]?.asString) {
        null, "signed16Tenths" -> ResistanceControlFormat.SINT16_TENTHS
        "uint8Tenths" -> ResistanceControlFormat.UINT8_TENTHS
        else -> error("Unknown control format")
    }

    @Test fun values() {
        val base = "shared/conformance/values"
        val paths = listOf("$base/v1/schema.json", "$base/v1/vectors.json", "$base/README.md")
        Corpus.Run("values-v1", paths).execute(8, 16) {
            val document = Corpus.read(paths[1])
            Corpus.validate(Corpus.read(paths[0]), document)
            val fixtures = document.cases("cases")
            Corpus.unique(fixtures)
            fixtures.groupBy { it["operation"].asString }.forEach { (category, rows) -> cases(category, rows) }
            fixtures.forEach { row ->
                val id = row["id"].asString
                val category = row["operation"].asString
                assertion(id, category, "encode") {
                    val actual = when (category) {
                        "features" -> FeatureCodec.encode(Features(row["machine"].asLong, row["target"].asLong))
                        "range" -> RangeCodec.encode(range(row))
                        else -> error("Unknown category $category")
                    }
                    Corpus.exact(row["expectedBytes"], wire(actual))
                }
                assertion(id, category, "decode") {
                    val bytes = Corpus.bytes(row["expectedBytes"])
                    val expected = row.deepCopy().apply { remove("id"); remove("operation"); remove("expectedBytes") }
                    val actual = when (category) {
                        "features" -> FeatureCodec.decode(bytes).let { Corpus.json(mapOf("machine" to it.machine, "target" to it.target)) }
                        "range" -> rawRange(RangeCodec.decode(kind(row["kind"].asString), bytes))
                        else -> error("Unknown category $category")
                    }
                    Corpus.exact(expected, actual)
                }
            }
        }
    }

    @Test fun controls() {
        val base = "shared/conformance/controls"
        val paths = listOf("$base/v1/schema.json", "$base/v1/vectors.json", "$base/README.md")
        Corpus.Run("controls-v1", paths).execute(41, 72) {
            val document = Corpus.read(paths[1])
            Corpus.validate(Corpus.read(paths[0]), document)
            val categories = listOf("requests", "responses", "invalid")
            Corpus.unique(categories.flatMap { document.cases(it) })
            categories.forEach { category ->
                val fixtures = document.cases(category)
                cases(category, fixtures)
                fixtures.forEach { row ->
                    val id = row["id"].asString
                    val request = row["operation"].asString == "request"
                    assertion(id, category, "decode") {
                        val bytes = Corpus.bytes(row["bytes"])
                        if (category == "invalid") {
                            val failure = assertFailsWith<FtmsException> {
                                if (request) ControlCodec.decodeRequest(bytes, format(row)) else ControlCodec.decodeResponse(bytes)
                            }
                            assertEquals(row["error"].asString, failure.error.name.lowercase())
                        } else {
                            val actual = if (request) ControlCodec.decodeRequest(bytes, format(row)).let {
                                Corpus.json(mapOf("opcode" to it.opcode, "operands" to it.operands().toList()))
                            } else rawResponse(ControlCodec.decodeResponse(bytes))
                            Corpus.exact(row["decoded"], actual)
                        }
                    }
                    if (category != "invalid" && row["encode"]?.asBoolean != false) assertion(id, category, "encode") {
                        val raw = row.getAsJsonObject("decoded")
                        val actual = if (request) ControlCodec.encodeRequest(ControlRequest(raw.int("opcode"),
                            raw.getAsJsonArray("operands").map { it.asLong }.toLongArray()), format(row))
                        else ControlCodec.encodeResponse(response(raw))
                        Corpus.exact(row["bytes"], wire(actual))
                    }
                }
            }
        }
    }

    @Test fun inspection() {
        val base = "shared/conformance/inspection/v1"
        // This contract has no shared schema. The strict port-owned schema is also hashed.
        val schema = "packages/kotlin/src/test/kotlin/io/github/deancochran/ftms/foundation/inspection-schema.json"
        val paths = listOf("$base/fixtures.json", "$base/README.md", schema)
        Corpus.Run("inspection-v1", paths).execute(9, 9) {
            val document = Corpus.read(paths[0])
            Corpus.validate(Corpus.read(schema), document)
            val fixtures = document.cases("cases")
            Corpus.unique(fixtures)
            fixtures.groupBy { it["kind"].asString }.forEach { (category, rows) -> cases(category, rows) }
            fixtures.forEach { row -> assertion(row["id"].asString, row["kind"].asString, "inspect") {
                val format = when (row.getAsJsonObject("options")?.get("resistanceFormat")?.asString) {
                    null, "uint8Whole" -> ResistanceRangeFormat.UINT8_WHOLE
                    "signed16Tenths" -> ResistanceRangeFormat.SINT16_TENTHS
                    else -> error("Unknown range format")
                }
                val actual = RangeCodec.inspect(kind(row["kind"].asString), Corpus.bytes(row["bytes"]), format)
                val report = Corpus.json(mapOf("selectedProfile" to profile(actual.selectedProfile),
                    "actualLength" to actual.actualLength, "expectedLength" to actual.expectedLength,
                    "status" to actual.status.name.lowercase(), "value" to rawRange(actual.value),
                    "candidates" to actual.candidates.map { mapOf("profile" to profile(it.profile),
                        "expectedLength" to it.expectedLength, "status" to it.status.name.lowercase(), "value" to rawRange(it.value)) }))
                Corpus.exact(row["expected"], report)
            } }
        }
    }
}
