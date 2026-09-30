package io.github.deancochran.ftms.measurement

import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.fasterxml.jackson.databind.ObjectMapper
import com.networknt.schema.JsonSchemaFactory
import com.networknt.schema.SpecVersion
import org.junit.jupiter.api.Assertions.assertEquals
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/** Test-only canonical adapter, independent of production layout tables. */
internal object RawCorpusSupport {
    val root: Path = generateSequence(Path.of(System.getProperty("ftms.root", ".")).toAbsolutePath()) { it.parent }
        .first { Files.isDirectory(it.resolve("shared/conformance")) }
    fun load(relative: String): JsonObject = JsonParser.parseString(Files.readString(root.resolve(relative))).asJsonObject
    fun validate(schemaPath: String, document: JsonObject) {
        val mapper = ObjectMapper()
        val schema = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012)
            .getSchema(mapper.readTree(Files.readString(root.resolve(schemaPath))))
        val errors = schema.validate(mapper.readTree(document.toString()))
        check(errors.isEmpty()) { "Canonical schema failure: ${errors.joinToString()}" }
    }
    fun bytes(json: JsonElement): ByteArray = json.asJsonArray.map { it.asInt.toByte() }.toByteArray()
    fun ints(json: JsonElement): IntArray = json.asJsonArray.map { it.asInt }.toIntArray()
    fun array(values: IntArray): JsonArray = JsonArray().apply { values.forEach { add(it) } }
    fun flag(value: Boolean): Int = if (value) 1 else 0

    /** Recursive exact keys, JSON types, integers, nulls, and ordered arrays. */
    fun exact(expected: JsonElement, actual: JsonElement, path: String = "$") {
        when {
            expected.isJsonObject -> {
                assertEquals(true, actual.isJsonObject, "$path object type")
                assertEquals(expected.asJsonObject.keySet(), actual.asJsonObject.keySet(), "$path keys")
                expected.asJsonObject.entrySet().forEach { (key, value) -> exact(value, actual.asJsonObject[key], "$path.$key") }
            }
            expected.isJsonArray -> {
                assertEquals(true, actual.isJsonArray, "$path array type")
                assertEquals(expected.asJsonArray.size(), actual.asJsonArray.size(), "$path length")
                expected.asJsonArray.forEachIndexed { i, value -> exact(value, actual.asJsonArray[i], "$path[$i]") }
            }
            expected.isJsonNull -> assertEquals(true, actual.isJsonNull, "$path null")
            else -> {
                assertEquals(true, actual.isJsonPrimitive, "$path primitive type")
                val e = expected.asJsonPrimitive
                val a = actual.asJsonPrimitive
                assertEquals(e.isNumber, a.isNumber, "$path numeric type")
                assertEquals(e.isBoolean, a.isBoolean, "$path boolean type")
                assertEquals(e.isString, a.isString, "$path string type")
                if (e.isNumber) assertEquals(e.asBigDecimal.toBigIntegerExact(), a.asBigDecimal.toBigIntegerExact(), path)
                else assertEquals(e, a, path)
            }
        }
    }

    fun measurementJson(value: Measurement): JsonObject = JsonObject().apply {
        addProperty("kind", value.kind.ordinal); addProperty("flags", value.flags)
        addProperty("present", value.present); addProperty("unavailable", value.unavailable)
        add("values", array(value.values)); addProperty("moreData", flag(value.moreData))
        addProperty("backward", flag(value.backward)); addProperty("truncated", flag(value.truncated))
        addProperty("trailingBytes", flag(value.trailingBytes)); addProperty("reservedFlags", flag(value.reservedFlags))
        addProperty("bytesRead", value.bytesRead)
    }
    fun measurementInput(json: JsonObject): Measurement = Measurement(
        MeasurementKind.entries[json["kind"].asInt], json["flags"].asInt, json["present"].asLong,
        json["unavailable"].asLong, ints(json["values"]), json["moreData"].asInt == 1,
        json["backward"].asInt == 1, json["truncated"].asInt == 1,
        json["trailingBytes"].asInt == 1, json["reservedFlags"].asInt == 1, json["bytesRead"].asInt,
    )
    fun identity(vararg paths: String) {
        fun git(vararg args: String): String {
            val process = ProcessBuilder(listOf("git", "-C", root.toString()) + args).redirectErrorStream(true).start()
            val text = process.inputStream.bufferedReader().readText().trim()
            check(process.waitFor() == 0) { "Unable to identify corpus checkout: $text" }
            return text
        }
        println("corpus source=${git("rev-parse", "HEAD")} dirty=${git("status", "--porcelain").isNotEmpty()}")
        for (path in paths) {
            val hash = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(root.resolve(path)))
                .joinToString("") { "%02x".format(it.toInt() and 255) }
            println("sha256 $path $hash")
        }
    }
    class Accounting(private val family: String) {
        private val ids = mutableSetOf<String>()
        private val failures = mutableListOf<String>()
        private var assertions = 0
        private val categories = linkedMapOf<String, Int>()
        fun case(id: String, category: String) {
            check(ids.add(id)) { "Duplicate corpus ID $id" }
            categories[category] = (categories[category] ?: 0) + 1
        }
        fun direction(id: String, direction: String, block: () -> Unit) {
            assertions++
            try {
                block()
                println("$family $id $direction PASS")
            } catch (error: AssertionError) { failures.add("$id $direction: $error")
            } catch (error: Exception) { failures.add("$id $direction: $error") }
        }
        fun finish(cases: Int, directions: Int) {
            println("$family schemaVersion=1 categories=$categories cases=${ids.size} assertions=$assertions passed=${assertions - failures.size} failed=${failures.size} unsupported=0 skipped=0")
            failures.forEach { println("FAIL $it") }
            assertEquals(cases, ids.size, "$family case accounting")
            assertEquals(directions, assertions, "$family direction accounting")
            assertEquals(emptyList<String>(), failures, "$family failures")
        }
    }
}
