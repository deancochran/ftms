package io.github.deancochran.ftms.capability

import com.google.gson.JsonElement
import com.google.gson.JsonParser
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

public class CapabilityFixtureContractTest {
    private fun json(text: String): JsonElement = JsonParser.parseString(text)
    private fun expand(edits: String): JsonElement = CapabilityFixtures.expand(
        json("""{"base":{"rows":[{"x":1,"values":[]},{"x":2,"values":[]}],"tail":[1,2,3]}}""").asJsonObject,
        json("""{"template":"base","edits":$edits}""").asJsonObject
    )

    @Test public fun rootReplacementAndOrderedEditsAreLiteral(): Unit {
        assertEquals(json("""{"items":[7,9]}"""), expand("""[
          {"path":[],"value":{"items":[1,2,3]}},
          {"op":"remove","path":["items",0]},
          {"path":["items",0],"value":7},
          {"op":"remove","path":["items",1]},
          {"op":"append","path":["items"],"value":9}
        ]"""))
        assertEquals(json("null"), expand("""[{"path":[],"value":null}]"""))
    }

    @Test public fun replacementsSelectArraysAndDoNotAliasTemplatesOrValues(): Unit {
        val templates = json("""{"base":{"rows":[{"x":1},{"x":2}]}}""").asJsonObject
        val original = templates.deepCopy()
        val edits = json("""{"template":"base","edits":[
          {"path":["rows","*","x"],"value":{"v":1}},
          {"path":["rows",0,"x","v"],"value":9},
          {"path":["rows",[1],"x","v"],"value":4}
        ]}""").asJsonObject
        val originalEdits = edits.deepCopy()
        assertEquals(json("""{"rows":[{"x":{"v":9}},{"x":{"v":4}}]}"""), CapabilityFixtures.expand(templates, edits))
        assertEquals(original, templates)
        assertEquals(originalEdits, edits)
        assertEquals(CapabilityFixtures.expand(templates, edits), CapabilityFixtures.expand(templates, edits))
    }

    @Test public fun invalidEditsAreRejected(): Unit {
        val invalid = listOf(
            """{"op":"append","path":["rows","*","values"],"value":1}""",
            """{"op":"append","path":["rows",[0],"values"],"value":1}""",
            """{"op":"remove","path":["rows","*"]}""",
            """{"op":"remove","path":["rows",[0]]}""",
            """{"op":"remove","path":[]}""",
            """{"op":"append","path":[],"value":1}""",
            """{"path":["rows",[0,0]],"value":1}""",
            """{"path":["rows",[]],"value":1}""",
            """{"path":["rows",[2]],"value":1}""",
            """{"path":["rows","0"],"value":1}""",
            """{"path":["rows",-1],"value":1}""",
            """{"path":["rows",0.5],"value":1}""",
            """{"path":["rows",4294967296],"value":1}""",
            """{"path":["rows",true],"value":1}""",
            """{"path":["missing"],"value":1}""",
            """{"op":"remove","path":["missing"]}""",
            """{"path":[0],"value":1}""",
            """{"path":["*"],"value":1}""",
            """{"path":["rows",0,"x",0],"value":1}""",
            """{"op":"append","path":["rows",0,"x"],"value":1}""",
            """{"op":"merge","path":["rows"],"value":1}""",
            """{"path":["rows"]}""",
            """{"op":"remove","path":["rows"],"value":1}""",
            """{"path":["rows"],"value":1,"extra":true}""",
            """{"path":"rows","value":1}"""
        )
        for (edit in invalid) assertThrows(RuntimeException::class.java, { expand("[$edit]") }, edit)
        assertThrows(IllegalArgumentException::class.java) {
            CapabilityFixtures.expand(json("{}").asJsonObject, json("""{"template":"missing","edits":[]}""").asJsonObject)
        }
    }

    @Test public fun entireRootAndExpandedValuesAreSchemaValidated(): Unit {
        val source = CapabilityFixtures.source()
        CapabilityFixtures.validate(source)
        val extra = source.deepCopy().apply { addProperty("unknown", 1) }
        assertThrows(IllegalArgumentException::class.java) { CapabilityFixtures.validate(extra) }
        val badTemplate = source.deepCopy()
        badTemplate.getAsJsonObject("snapshots").entrySet().first().value.asJsonObject.addProperty("generation", -1)
        assertThrows(IllegalArgumentException::class.java) { CapabilityFixtures.validate(badTemplate) }
        val input = source.getAsJsonObject("snapshots").entrySet().first().value.deepCopy().asJsonObject
        input.addProperty("generation", true)
        assertThrows(IllegalArgumentException::class.java) { CapabilityFixtures.validate(input, "snapshot") }
        val read = json("""{"discovery":2,"scope":1,"generation":0,"characteristics":[
          {"uuid":"00002acc00001000800000805f9b34fb","properties":2,"readState":0,"reason":0,"bytes":"00"}
        ]}""")
        assertThrows(IllegalArgumentException::class.java) { CapabilityFixtures.validate(read, "snapshot") }
        val report = source.getAsJsonObject("reports").entrySet().first().value.deepCopy().asJsonObject
        report.getAsJsonArray("feature").set(0, json("true"))
        assertThrows(IllegalArgumentException::class.java) { CapabilityFixtures.validate(report, "report") }
        val expansion = json("""{"template":"base","edits":[{"path":["generation"],"value":-1}]}""").asJsonObject
        val templates = json("{}").asJsonObject.apply {
            add("base", source.getAsJsonObject("snapshots").entrySet().first().value)
        }
        assertThrows(IllegalArgumentException::class.java) {
            CapabilityFixtures.validate(CapabilityFixtures.expand(templates, expansion), "snapshot")
        }
        val invalidExpected = source.getAsJsonObject("reports").entrySet().first().value.deepCopy().asJsonObject
        invalidExpected.getAsJsonArray("operations").remove(0)
        assertThrows(IllegalArgumentException::class.java) { CapabilityFixtures.validate(invalidExpected, "report") }
    }

    @Test public fun accountingReportsEveryFailureAndNeverCallsDriverForInvalidSource(): Unit {
        val source = CapabilityFixtures.source()
        val total = source.getAsJsonArray("cases").size()
        val failedDriver = CapabilityFixtures.run(source) { error("deliberate driver failure") }
        assertEquals(total, failedDriver["total"].asInt)
        assertEquals(total, failedDriver["failed"].asInt)
        assertEquals(0, failedDriver["passed"].asInt)
        assertEquals(0, failedDriver["unsupported"].asInt)
        assertEquals(0, failedDriver["skipped"].asInt)
        assertFalse(failedDriver["complete"].asBoolean)
        assertEquals(total, failedDriver.getAsJsonArray("cases").size())
        assertEquals(total, failedDriver.getAsJsonObject("categoryCounts").entrySet().sumOf { it.value.asInt })
        assertTrue(failedDriver.getAsJsonArray("cases").all {
            it.asJsonObject["outcome"].asString == "failed" && it.asJsonObject["reason"].asString.contains("deliberate driver failure")
        })
        source.addProperty("invalid", true)
        var called = false
        val invalidSource = CapabilityFixtures.run(source) { called = true; error("must not run") }
        assertFalse(called)
        assertFalse(invalidSource["complete"].asBoolean)
        assertEquals(total, invalidSource["failed"].asInt)
        assertEquals(total, invalidSource.getAsJsonArray("cases").size())
        val empty = CapabilityFixtures.source().apply { getAsJsonArray("cases").asList().clear() }
        assertFalse(CapabilityFixtures.run(empty) { error("must not run") }["complete"].asBoolean)
    }

    @Test public fun duplicateIdsAndInvalidExpandedExpectationsAreAccountedFailures(): Unit {
        val source = CapabilityFixtures.source()
        val first = source.getAsJsonArray("cases")[0].deepCopy().asJsonObject
        source.add("cases", json("[]").asJsonArray.apply { add(first); add(first.deepCopy()) })
        val expected = CapabilityFixtures.expand(source.getAsJsonObject("reports"), first.getAsJsonObject("expected")).asJsonObject
        val duplicate = CapabilityFixtures.run(source) { expected.deepCopy() }
        assertEquals(1, duplicate["passed"].asInt)
        assertEquals(1, duplicate["failed"].asInt)
        assertFalse(duplicate["complete"].asBoolean)
        assertTrue(duplicate.getAsJsonArray("cases")[1].asJsonObject["reason"].asString.contains("duplicate fixture id"))
        source.add("cases", json("[]").asJsonArray.apply { add(first) })
        first.getAsJsonObject("expected").getAsJsonArray("edits").add(json("""{"path":["feature",0],"value":true}"""))
        var called = false
        val invalid = CapabilityFixtures.run(source) { called = true; expected.deepCopy() }
        assertFalse(called)
        assertEquals(1, invalid["failed"].asInt)
        assertFalse(invalid["complete"].asBoolean)
        assertTrue(invalid.getAsJsonArray("cases")[0].asJsonObject["reason"].asString.contains("report schema violations"))
    }
}
