package io.github.deancochran.ftms.foundation

import com.fasterxml.jackson.databind.ObjectMapper
import com.google.gson.GsonBuilder
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.networknt.schema.JsonSchemaFactory
import com.networknt.schema.SpecVersion
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/** Test-only canonical loader, schema validator, exact comparator and accounting. */
internal object Corpus {
    val root: Path = Path.of("../..").toAbsolutePath().normalize()
    val gson = GsonBuilder().serializeNulls().setPrettyPrinting().create()

    fun read(path: String): JsonObject = JsonParser.parseString(Files.readString(root.resolve(path))).asJsonObject

    fun validate(schema: JsonObject, document: JsonObject) {
        val mapper = ObjectMapper()
        val validator = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012)
            .getSchema(mapper.readTree(schema.toString()))
        val errors = validator.validate(mapper.readTree(document.toString()))
        check(errors.isEmpty()) { "Schema validation failed: ${errors.joinToString()}" }
    }

    fun unique(cases: List<JsonObject>) {
        val ids = cases.map { it["id"].asString }
        check(ids.isNotEmpty() && ids.toSet().size == ids.size) { "Empty corpus or duplicate IDs" }
    }

    /** Gson's default equality conflates integer and fractional numeric forms. */
    fun exact(expected: JsonElement, actual: JsonElement, path: String = "$") {
        when {
            expected.isJsonNull -> check(actual.isJsonNull) { "$path: expected null, got $actual" }
            expected.isJsonObject -> {
                check(actual.isJsonObject) { "$path: expected object, got $actual" }
                check(expected.asJsonObject.keySet() == actual.asJsonObject.keySet()) { "$path: keys differ: $expected / $actual" }
                expected.asJsonObject.entrySet().forEach { (key, value) -> exact(value, actual.asJsonObject[key], "$path.$key") }
            }
            expected.isJsonArray -> {
                check(actual.isJsonArray && expected.asJsonArray.size() == actual.asJsonArray.size()) { "$path: array length/type differs" }
                expected.asJsonArray.forEachIndexed { index, value -> exact(value, actual.asJsonArray[index], "$path[$index]") }
            }
            else -> {
                check(actual.isJsonPrimitive) { "$path: expected primitive, got $actual" }
                val e = expected.asJsonPrimitive
                val a = actual.asJsonPrimitive
                check(e.isNumber == a.isNumber && e.isBoolean == a.isBoolean && e.isString == a.isString) { "$path: primitive types differ" }
                if (e.isNumber) {
                    check(e.toString().matches(Regex("-?(0|[1-9][0-9]*)")) && a.toString().matches(Regex("-?(0|[1-9][0-9]*)"))) { "$path: non-integer numeric representation" }
                    check(e.asBigInteger == a.asBigInteger) { "$path: expected $e, got $a" }
                } else check(e == a) { "$path: expected $e, got $a" }
            }
        }
    }

    fun json(value: Any?): JsonElement = gson.toJsonTree(value)
    fun bytes(value: JsonElement): ByteArray = value.asJsonArray.map {
        val integer = it.asInt
        check(integer in 0..255 && it.toString() == integer.toString()) { "Invalid byte: $it" }
        integer.toByte()
    }.toByteArray()

    private fun git(vararg args: String): String {
        val process = ProcessBuilder(listOf("git", "-C", root.toString()) + args).redirectErrorStream(true).start()
        val output = process.inputStream.bufferedReader().readText().trim()
        check(process.waitFor() == 0) { "Git identity failed: $output" }
        return output
    }

    class Run(private val name: String, private val paths: List<String>) {
        private val outcomes = mutableListOf<Map<String, Any?>>()
        private val categories = linkedMapOf<String, Int>()
        private val runnerErrors = mutableListOf<String>()
        private var discovered = 0

        fun cases(category: String, cases: List<JsonObject>) {
            check(category !in categories)
            categories[category] = cases.size
            discovered += cases.size
        }

        fun assertion(id: String, category: String, direction: String, action: () -> Unit) {
            var reason: String? = null
            try { action() } catch (failure: Throwable) {
                reason = "${failure.javaClass.name}: ${failure.message}"
                if (failure !is AssertionError && failure !is IllegalStateException) runnerErrors.add("$id/$direction: $reason")
            }
            outcomes.add(mapOf("id" to id, "category" to category, "direction" to direction,
                "outcome" to if (reason == null) "pass" else "fail", "reason" to reason))
        }

        fun execute(expectedCases: Int, expectedAssertions: Int, action: Run.() -> Unit) {
            try { action() } catch (failure: Throwable) { runnerErrors.add("${failure.javaClass.name}: ${failure.message}") }
            if (discovered != expectedCases || outcomes.size != expectedAssertions) {
                runnerErrors.add("Accounting mismatch: $discovered/$expectedCases cases, ${outcomes.size}/$expectedAssertions assertions")
            }
            val byId = outcomes.groupBy { it["id"] }
            if (byId.size != discovered) runnerErrors.add("Not every discovered case executed")
            val failed = outcomes.count { it["outcome"] != "pass" }
            val hashes = paths.associateWith { path -> MessageDigest.getInstance("SHA-256")
                .digest(Files.readAllBytes(root.resolve(path))).joinToString("") { "%02x".format(it) } }
            val report = mapOf("corpus" to name, "schemaVersion" to 1, "head" to git("rev-parse", "HEAD"),
                "dirty" to git("status", "--porcelain", "--untracked-files=all").isNotEmpty(), "sha256" to hashes,
                "cases" to discovered, "categories" to categories, "passedCases" to byId.count { (_, entries) -> entries.all { it["outcome"] == "pass" } },
                "failedCases" to byId.count { (_, entries) -> entries.any { it["outcome"] != "pass" } },
                "assertions" to outcomes.size, "passedAssertions" to outcomes.size - failed, "failedAssertions" to failed,
                "unsupported" to 0, "skipped" to 0, "runnerErrors" to runnerErrors, "outcomes" to outcomes,
                "complete" to (runnerErrors.isEmpty() && failed == 0 && discovered > 0))
            val destination = Path.of("build/conformance/$name.json")
            Files.createDirectories(destination.parent)
            Files.writeString(destination, gson.toJson(report) + "\n")
            check(runnerErrors.isEmpty() && failed == 0) { "See $destination: $failed failures; $runnerErrors" }
        }
    }
}
