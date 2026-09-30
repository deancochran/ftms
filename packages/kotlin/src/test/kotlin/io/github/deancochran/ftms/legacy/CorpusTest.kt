package io.github.deancochran.ftms.legacy

import com.fasterxml.jackson.databind.ObjectMapper
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.networknt.schema.JsonSchemaFactory
import com.networknt.schema.SpecVersion
import io.github.deancochran.ftms.*
import io.github.deancochran.ftms.measurement.*
import org.junit.jupiter.api.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/** Reads only canonical files. ftms.repositoryRoot permits an isolated compilation checkout. */
class CorpusTest {
    private val root: Path = System.getProperty("ftms.repositoryRoot")?.let { Path.of(it).toAbsolutePath() }
        ?: generateSequence(Path.of("").toAbsolutePath()) { it.parent }.first { Files.isDirectory(it.resolve("shared/conformance/v1")) }
    private val categories = listOf("features", "ranges", "controls", "controlResponses", "measurements", "statuses", "diagnostics")
    private data class Case(val category: String, val id: String, val action: () -> Unit)
    private data class Outcome(val category: String, val id: String, val outcome: String, val reason: String? = null)
    private fun hash(path: Path) = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)).joinToString("") { "%02x".format(it) }
    private fun git(vararg args: String): String {
        val p = ProcessBuilder(listOf("git") + args).directory(root.toFile()).redirectErrorStream(true).start()
        val output = p.inputStream.bufferedReader().readText().trim()
        check(p.waitFor() == 0) { "Git provenance unavailable: $output" }; return output
    }
    private fun runCorpus(name: String, directory: String, contract: String, cases: (JsonObject) -> List<Case>, checks: (JsonObject, JsonObject) -> Unit) {
        val dir = root.resolve(directory); val outcomes = mutableListOf<Outcome>(); val errors = mutableListOf<String>()
        var discovered = emptyList<Case>(); var schemaVersion: Int? = null; var sourceCommit: String? = null; var dirty: Boolean? = null
        val hashes = linkedMapOf<String, String>()
        try {
            sourceCommit = git("rev-parse", "HEAD"); dirty = git("status", "--porcelain").isNotEmpty()
            hashes["schemaSha256"] = hash(dir.resolve("schema.json")); hashes["vectorsSha256"] = hash(dir.resolve("vectors.json"))
            hashes["contractSha256"] = hash(root.resolve(contract))
            val text = Files.readString(dir.resolve("vectors.json")); val schemaText = Files.readString(dir.resolve("schema.json"))
            val vectors = JsonParser.parseString(text).asJsonObject; val schema = JsonParser.parseString(schemaText).asJsonObject
            schemaVersion = vectors.int("schemaVersion")
            discovered = cases(vectors)
            val validator = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(ObjectMapper().readTree(schemaText))
            val violations = validator.validate(ObjectMapper().readTree(text))
            demand(violations.isEmpty(), "Exact canonical schema validation failed: $violations")
            checks(vectors, schema)
            for (case in discovered) {
                try { case.action(); outcomes += Outcome(case.category, case.id, "passed") }
                catch (e: AssertionError) { outcomes += Outcome(case.category, case.id, "failed", e.message ?: e.toString()) }
                catch (e: Exception) { outcomes += Outcome(case.category, case.id, "failed", e.toString()) }
            }
        } catch (e: AssertionError) { errors += e.message ?: e.toString() }
        catch (e: Exception) { errors += e.toString() }
        val skipped = discovered.filter { c -> outcomes.none { it.category == c.category && it.id == c.id } }
            .map { Outcome(it.category, it.id, "skipped", "Runner validation/provenance failed before execution") }
        val all = outcomes + skipped
        val complete = discovered.isNotEmpty() && errors.isEmpty() && all.all { it.outcome == "passed" } && outcomes.size == discovered.size
        val report = linkedMapOf<String, Any?>("runner" to "Kotlin JUnit original-v1/compatibility consumer", "corpus" to name,
            "sourceCommit" to sourceCommit, "dirty" to dirty, "schemaVersion" to schemaVersion,
            "schemaValidator" to "networknt JSON Schema draft 2020-12", "expectedCategoryCounts" to discovered.groupingBy { it.category }.eachCount(),
            "categoryCounts" to outcomes.groupingBy { it.category }.eachCount(), "total" to discovered.size,
            "passed" to all.count { it.outcome == "passed" }, "failed" to all.count { it.outcome == "failed" },
            "unsupported" to 0, "skipped" to skipped.size, "outcomes" to all, "runnerErrors" to errors, "complete" to complete)
        report.putAll(hashes)
        val output = System.getProperty("ftms.reportDirectory")?.let { Path.of(it) } ?: Path.of("build/reports/conformance")
        Files.createDirectories(output); Files.writeString(output.resolve("$name.json"), gson.toJson(report))
        demand(complete, "$name incomplete: ${gson.toJson(report)}")
    }

    @Test fun originalV1() = runCorpus("original-v1", "shared/conformance/v1", "shared/conformance/README.md", { vectors ->
        categories.flatMap { category -> vectors.getAsJsonArray(category).map { element ->
            val v = element.asJsonObject; Case(category, v.text("id")) { originalCase(category, v) }
        } }
    }, { vectors, schema ->
        demand(vectors.text("\$schema") == "./schema.json" && vectors.int("schemaVersion") == 1, "v1 identity")
        demand(schema.text("\$id").endsWith("/v0.2.0/conformance/v1/schema.json"), "Historical schema identity changed")
        val all = categories.flatMap { vectors.getAsJsonArray(it).map { v -> v.asJsonObject } }
        demand(all.size == 97, "Expected 97 original-v1 cases, discovered ${all.size}")
        demand(categories.map { vectors.getAsJsonArray(it).size() } == listOf(35,7,21,12,8,4,10), "v1 category counts changed")
        demand(all.map { it.text("id") }.toSet().size == all.size, "Duplicate v1 IDs")
        val sources = vectors.getAsJsonArray("provenance").map { it.asJsonObject.text("id") }.toSet()
        val errata = vectors.getAsJsonArray("errata").map { it.asJsonObject }
        demand(errata.map { it.text("id") }.containsAll(listOf("E8991", "E9135", "EC23224")), "Mandatory errata absent")
        for (v in all + errata) {
            val refs = v.getAsJsonArray("source"); demand(refs.size() > 0, "Empty provenance")
            refs.forEach { demand(it.asString in sources, "Unresolved source $it") }
        }
    })

    private fun originalCase(category: String, v: JsonObject) {
        when(category) {
            "features" -> {
                val actual = NormalizedAdapter.features(v.bytes())
                if(v.has("expected")) exact(json(actual), v["expected"])
                else exact(json(actual.filterValues { it }.keys.sorted()), json(v.getAsJsonArray("expectedTrue").map { it.asString }.sorted()))
            }
            "ranges" -> if(v.has("expectedError")) {
                val result = try { mapOf("ok" to true, "value" to NormalizedAdapter.range(v.text("kind"),v.bytes())) }
                    catch(e: FtmsException) { mapOf("ok" to false, "error" to mapOf("code" to e.error.name.lowercase())) }
                subset(json(result), json(mapOf("ok" to false, "error" to mapOf("code" to v.text("expectedError")))))
            } else {
                val expected = v.getAsJsonObject("expected").deepCopy().apply { addProperty("kind",v.text("kind")) }
                exact(json(NormalizedAdapter.range(v.text("kind"),v.bytes())), expected)
            }
            "controls" -> exact(json(NormalizedAdapter.request(v.getAsJsonObject("request")).map { it.toInt() and 255 }),v["expectedBytes"])
            "controlResponses" -> if(v.has("expectedError")) {
                val result = try { mapOf("ok" to true, "value" to NormalizedAdapter.response(v.bytes())) }
                    catch(e: FtmsException) {
                        if(e.error !in listOf(FtmsError.LENGTH, FtmsError.KIND)) throw e
                        mapOf("ok" to false, "error" to mapOf("code" to "malformed_response"))
                    }
                subset(json(result), json(mapOf("ok" to false, "error" to mapOf("code" to v.text("expectedError")))))
            } else exact(json(NormalizedAdapter.response(v.bytes())), v["expected"])
            "measurements", "statuses", "diagnostics" -> {
                val parsed = NormalizedAdapter.parse(v.text("characteristicUuid"),v.bytes())
                if(category == "measurements") demand(parsed.status.isEmpty(), "Expected measurement")
                if(v.has("expectedMetrics")) metrics(json(parsed.metrics),v["expectedMetrics"])
                if(v.has("expectedStatus")) subset(json(parsed.status),v["expectedStatus"])
                if(category == "diagnostics") {
                    exact(json(parsed.truncated),v["expectedTruncated"])
                    for(code in v.getAsJsonArray("expectedIssues")) demand(code.asString in parsed.issues,"Missing diagnostic $code; actual ${parsed.issues}")
                    if(v.has("expectedStatusCode")) {
                        demand(parsed.status.containsKey("code"), "Missing status code")
                        exact(json(parsed.status["code"]),v["expectedStatusCode"])
                    }
                }
            }
            else -> error("Unsupported category $category")
        }
    }

    @Test fun compatibility() = runCorpus("compatibility-v1", "shared/conformance/compatibility/v1", "shared/conformance/compatibility/README.md", { vectors ->
        vectors.getAsJsonArray("cases").flatMap { element ->
            val v = element.asJsonObject
            listOf("decode", "encode").map { direction -> Case("${v.text("area")}-$direction", "${v.text("id")}:$direction") { compatibilityCase(v,direction) } }
        }
    }, { vectors, _ ->
        demand(vectors.int("schemaVersion") == 1, "Compatibility schema version")
        val cases = vectors.getAsJsonArray("cases").map { it.asJsonObject }
        demand(cases.isNotEmpty(), "Empty compatibility corpus")
        demand(cases.map { it.text("id") }.toSet().size == cases.size, "Duplicate compatibility IDs")
    })

    private fun compatibilityCase(v: JsonObject, direction: String) {
        val e = v.getAsJsonObject("expected"); val options = v.getAsJsonObject("options")
        val signed = when(options.text("resistanceFormat")) { "signed16Tenths" -> true; "uint8Whole" -> false; else -> error("Unknown resistance format") }
        if(direction == "encode") demand(v["encode"].asBoolean, "Compatibility vector does not authorize encoding")
        if(v.text("area") == "measurement") {
            val pace = when(options.text("treadmillPaceFormat")) { "uint16" -> TreadmillPaceFormat.UINT16; "uint8Legacy" -> TreadmillPaceFormat.UINT8_LEGACY; else -> error("Unknown pace format") }
            val format = MeasurementFormat(if(signed) ResistanceFormat.SINT16_TENTHS else ResistanceFormat.UINT8_WHOLE,pace)
            if(direction == "decode") {
                val r = MeasurementCodec.decode(MeasurementKind.entries[v.int("kind")],v.bytes(),format)
                fun bit(b: Boolean) = if(b) 1 else 0
                exact(json(mapOf("kind" to r.kind.ordinal,"flags" to r.flags,"present" to r.present,"unavailable" to r.unavailable,
                    "values" to r.values.toList(),"moreData" to bit(r.moreData),"backward" to bit(r.backward),"truncated" to bit(r.truncated),
                    "trailingBytes" to bit(r.trailingBytes),"reservedFlags" to bit(r.reservedFlags),"bytesRead" to r.bytesRead)),e)
            } else {
                // Input is the independent literal expected object, never the result of decode.
                val r = Measurement(MeasurementKind.entries[e.int("kind")],e.int("flags"),e["present"].asLong,e["unavailable"].asLong,
                    e.getAsJsonArray("values").map { it.asInt }.toIntArray(),e.int("moreData") != 0,e.int("backward") != 0,
                    e.int("truncated") != 0,e.int("trailingBytes") != 0,e.int("reservedFlags") != 0,e.int("bytesRead"))
                exact(json(MeasurementCodec.encode(r,format).map { it.toInt() and 255 }),v["bytes"])
            }
        } else {
            demand(v.text("area") == "range", "Unsupported compatibility area")
            val format = if(signed) ResistanceRangeFormat.SINT16_TENTHS else ResistanceRangeFormat.UINT8_WHOLE
            if(direction == "decode") {
                val r = RangeCodec.decode(kind(v.text("kind")),v.bytes(),format)
                exact(json(mapOf("kind" to kindName(r.kind),"minimum" to r.minimum,"maximum" to r.maximum,"increment" to r.increment,
                    "scaleDivisor" to r.scaleDivisor,"unit" to r.unit.wire)),e)
            } else {
                val r = SupportedRange(kind(e.text("kind")),e.int("minimum"),e.int("maximum"),e.int("increment"),e.int("scaleDivisor"),RangeUnit.entries.single { it.wire == e.int("unit") })
                exact(json(RangeCodec.encode(r,format).map { it.toInt() and 255 }),v["bytes"])
            }
        }
    }
}
