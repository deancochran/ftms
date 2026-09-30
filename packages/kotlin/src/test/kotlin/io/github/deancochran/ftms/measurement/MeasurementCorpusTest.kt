package io.github.deancochran.ftms.measurement

import com.google.gson.JsonObject
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class MeasurementCorpusTest {
    @Test fun `canonical measurements all declared directions`() {
        val base = "shared/conformance/measurements"
        RawCorpusSupport.identity("$base/v1/schema.json", "$base/v1/vectors.json", "$base/README.md")
        val corpus = RawCorpusSupport.load("$base/v1/vectors.json")
        RawCorpusSupport.validate("$base/v1/schema.json", corpus)
        assertEquals(1, corpus["schemaVersion"].asInt)
        assertEquals(30, corpus["fieldOrder"].asJsonArray.size())
        val accounting = RawCorpusSupport.Accounting("measurements")
        for (element in corpus["cases"].asJsonArray) {
            val case = element.asJsonObject
            val id = case["id"].asString
            val kind = case["kind"].asInt
            val bytes = RawCorpusSupport.bytes(case["bytes"])
            val expected = case["decoded"].asJsonObject
            accounting.case(id, "kind-$kind")
            accounting.direction(id, "decode") {
                // Invalid kinds cannot be represented by the public enum; the adapter
                // rejects those before entering the codec. Short flags exercise decode.
                val actual = if (kind !in MeasurementKind.entries.indices) JsonObject().apply { addProperty("error", 3) }
                else try {
                    RawCorpusSupport.measurementJson(MeasurementCodec.decode(MeasurementKind.entries[kind], bytes))
                } catch (error: IllegalArgumentException) {
                    assertTrue(bytes.size < if (kind == 1) 3 else 2, "Unexpected decoder exception: $error")
                    JsonObject().apply { addProperty("error", 2) }
                }
                RawCorpusSupport.exact(expected, actual)
            }
            if (case["encode"].asBoolean) accounting.direction(id, "encode") {
                assertArrayEquals(bytes, MeasurementCodec.encode(RawCorpusSupport.measurementInput(expected)))
            } else assertTrue(case["reason"].asString.isNotBlank(), "$id decode-only reason")
        }
        accounting.finish(26, 47)
    }

    @Test fun `exact comparator rejects extra missing mistyped and reordered evidence`() {
        val expected = com.google.gson.JsonParser.parseString("""{"a":0,"b":null,"c":[1,2]}""")
        for (bad in listOf("""{"a":0,"b":null,"c":[1,2],"extra":0}""", """{"a":0,"c":[1,2]}""",
            """{"a":"0","b":null,"c":[1,2]}""", """{"a":false,"b":null,"c":[1,2]}""",
            """{"a":0,"b":null,"c":[2,1]}""", """{"a":0,"b":null,"c":[1]}""")) {
            assertThrows(AssertionError::class.java) { RawCorpusSupport.exact(expected, com.google.gson.JsonParser.parseString(bad)) }
        }
    }
}
