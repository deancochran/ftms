package io.github.deancochran.ftms.capability

import com.google.gson.JsonArray
import com.google.gson.JsonObject
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.assertTrue

/** Runs every canonical capability fixture without deriving expected output from the evaluator. */
public class CapabilityConformanceTest {
    @Test public fun canonicalCapabilityReportsMatchExactly(): Unit {
        val root = CapabilityFixtures.source()
        val accounting = CapabilityFixtures.identity(root)
        val results = CapabilityFixtures.run(root) { input -> normalize(FtmsCapabilityEvaluator.evaluate(snapshot(input))) }
        for ((key, value) in results.entrySet()) accounting.add(key, value)
        println("Capability conformance: $accounting")
        assertTrue(results["complete"].asBoolean, results.toString())
    }

    private fun snapshot(value: JsonObject): CapabilitySnapshot {
        val c7 = value.getAsJsonObject("c7")?.let { C7Evidence(truth(it["bondingSupported"].asInt), truth(it["featureMayChangeOverLifetime"].asInt)) }
        val characteristics = value.getAsJsonArray("characteristics").map { e ->
            val c = e.asJsonObject
            CharacteristicEvidence(c["uuid"].asString, c["properties"].asInt, ReadState.entries[c["readState"].asInt], ReadReason.entries[c["reason"].asInt], hex(c["bytes"].asString))
        }
        return CapabilitySnapshot(DiscoveryState.entries[value["discovery"].asInt], ServiceScope.entries[value["scope"].asInt], value["generation"].asLong, characteristics, c7)
    }
    private fun truth(value: Int): TruthValue = TruthValue.entries[value]
    private fun hex(value: String): ByteArray = ByteArray(value.length / 2) { i -> value.substring(i * 2, i * 2 + 2).toInt(16).toByte() }

    private fun normalize(report: CapabilityReport): JsonObject = JsonObject().apply {
        addProperty("generation", report.generation); addProperty("discovery", report.discovery.ordinal); addProperty("scope", report.scope.ordinal)
        addProperty("observationCount", report.observationCount); addProperty("diagnosticCount", report.diagnosticCount)
        add("presence", JsonArray().also { a -> report.presence.forEach { a.add(it.ordinal) } })
        add("feature", JsonArray().also { a -> a.add(report.feature.presence.ordinal); a.add(report.feature.decode.ordinal); nullable(a,report.feature.inputIndex); a.add(report.feature.machineRaw); a.add(report.feature.targetRaw); a.add(report.feature.machineUnknown); a.add(report.feature.targetUnknown) })
        add("ranges", JsonArray().also { a -> report.ranges.forEach { r -> a.add(JsonArray().also { x -> x.add(r.presence.ordinal); x.add(r.decode.ordinal); nullable(x,r.inputIndex); if(r.value==null)x.add(com.google.gson.JsonNull.INSTANCE) else x.add(JsonArray().also { v -> v.add(r.value.kind.ordinal); v.add(r.value.minimum); v.add(r.value.maximum); v.add(r.value.increment); v.add(r.value.scaleDivisor); v.add(listOf("km/h", "percent", "level", "bpm", "watts").indexOf(r.value.unit)) }) }) } })
        add("operations", JsonArray().also { a -> report.operations.forEach { o -> a.add(JsonArray().also { x -> x.add(o.opcode); if(o.targetBit==null)x.add(255) else x.add(o.targetBit); x.add(if(o.optionalInTable)1 else 0); x.add(o.declaration.ordinal); x.add(o.prerequisite.ordinal); x.add(o.reasons) }) } })
        add("observations", JsonArray().also { a -> report.observations.forEach { o -> a.add(JsonArray().also { x -> x.add(o.inputIndex);x.add(o.uuid);x.add(o.properties);x.add(o.knownKind.ordinal);x.add(o.readState.ordinal);x.add(o.readReason.ordinal);x.add(o.readSize) }) } })
        add("diagnostics", JsonArray().also { a -> report.diagnostics.forEach { d -> a.add(JsonArray().also { x -> x.add(d.code.ordinal);x.add(d.knownKind.ordinal);nullable(x,d.inputIndex) }) } })
    }
    private fun nullable(array: JsonArray, value: Int?): Unit { if(value==null) array.add(com.google.gson.JsonNull.INSTANCE) else array.add(value) }

}
