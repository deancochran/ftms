package io.github.deancochran.ftms.capability

import com.fasterxml.jackson.databind.ObjectMapper
import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.google.gson.JsonPrimitive
import com.networknt.schema.JsonSchemaFactory
import com.networknt.schema.SpecVersion
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.security.MessageDigest

/** Test-only literal expansion and validation; independent of protocol evaluation. */
internal object CapabilityFixtures {
    val repository: Path = generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
        .firstOrNull { Files.isRegularFile(it.resolve("shared/conformance/capabilities/v1/schema.json")) }
        ?: error("canonical capability schema not found")
    private val schemaText = Files.readString(repository.resolve("shared/conformance/capabilities/v1/schema.json"))
    private val mapper = ObjectMapper()
    private val factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012)
    private val schemas = listOf("root", "snapshot", "report").associateWith { definition ->
        val schema = JsonParser.parseString(schemaText).asJsonObject
        if (definition != "root") {
            // Keep the canonical definitions and dialect, and validate this definition as the root.
            schema.keySet().toList().filter { it !in setOf("\$schema", "\$id", "\$defs") }.forEach(schema::remove)
            schema.addProperty("\$ref", "#/\$defs/$definition")
        }
        factory.getSchema(mapper.readTree(schema.toString()))
    }

    fun source(): JsonObject = JsonParser.parseString(Files.readString(
        repository.resolve("shared/conformance/capabilities/v1/vectors.json")
    )).asJsonObject

    fun validate(value: JsonElement, definition: String = "root") {
        val errors = schemas.getValue(definition).validate(mapper.readTree(value.toString()))
        require(errors.isEmpty()) { "$definition schema violations: ${errors.joinToString()}" }
    }

    /** Account for every source case, including validation and driver failures. */
    fun run(root: JsonObject, driver: (JsonObject) -> JsonObject): JsonObject {
        val cases = root["cases"]?.takeIf { it.isJsonArray }?.asJsonArray ?: JsonArray()
        val outcomes = JsonArray()
        val categories = JsonObject()
        val errors = JsonArray()
        val sourceFailure = try { validate(root); null } catch (failure: Exception) {
            errors.add("corpus: $failure")
            failure
        }
        val ids = HashSet<String>()
        var passed = 0
        for ((position, case) in cases.withIndex()) {
            val item = case.takeIf { it.isJsonObject }?.asJsonObject
            val id = item?.get("id")?.takeIf { it is JsonPrimitive && it.isString }?.asString ?: "case-index-$position"
            val category = item?.get("category")?.takeIf { it is JsonPrimitive && it.isString }?.asString ?: "invalid"
            categories.addProperty(category, (categories[category]?.asInt ?: 0) + 1)
            val outcome = JsonObject().apply { addProperty("id", id); addProperty("category", category) }
            outcomes.add(outcome)
            fun failed(failure: Throwable) {
                outcome.addProperty("outcome", "failed")
                outcome.addProperty("reason", failure.toString())
                errors.add("$id: $failure")
            }
            try {
                require(sourceFailure == null) { "source schema validation failed: ${sourceFailure?.message}" }
                require(ids.add(id)) { "duplicate fixture id $id" }
                requireNotNull(item)
                val input = expand(root.getAsJsonObject("snapshots"), item.getAsJsonObject("input"))
                val expected = expand(root.getAsJsonObject("reports"), item.getAsJsonObject("expected"))
                validate(input, "snapshot")
                validate(expected, "report")
                val actual = driver(input.asJsonObject)
                validate(actual, "report")
                check(expected == actual) { "report mismatch: expected $expected, actual $actual" }
                outcome.addProperty("outcome", "passed")
                passed++
            } catch (failure: Exception) { failed(failure) }
            catch (failure: AssertionError) { failed(failure) }
        }
        return JsonObject().apply {
            addProperty("total", cases.size())
            addProperty("passed", passed)
            addProperty("failed", cases.size() - passed)
            addProperty("unsupported", 0)
            addProperty("skipped", 0)
            add("cases", outcomes)
            add("categoryCounts", categories)
            add("errors", errors)
            addProperty("complete", !cases.isEmpty && passed == cases.size() && errors.isEmpty)
        }
    }

    fun identity(root: JsonObject): JsonObject = JsonObject().apply {
        addProperty("gitHead", git("rev-parse", "HEAD"))
        addProperty("dirty", git("status", "--porcelain", "--untracked-files=all").isNotEmpty())
        add("schemaVersion", root["schemaVersion"])
        addProperty("comparisonContract", "urn:ftms:capabilities:conformance:v1")
        add("sha256", JsonObject().apply {
            for (file in listOf("shared/conformance/capabilities/v1/schema.json",
                "shared/conformance/capabilities/v1/vectors.json", "shared/conformance/capabilities/README.md",
                "shared/protocol/capability-discovery.md")) {
                addProperty(file, MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(repository.resolve(file)))
                    .joinToString("") { "%02x".format(it.toInt() and 255) })
            }
        })
    }

    private fun git(vararg args: String): String {
        val process = ProcessBuilder(listOf("git", "-C", repository.toString()) + args).redirectErrorStream(true).start()
        val output = process.inputStream.bufferedReader().readText().trim()
        check(process.waitFor() == 0) { "git identity command failed: $output" }
        return output
    }

    fun expand(templates: JsonObject, expansion: JsonObject): JsonElement {
        require(expansion.keySet() == setOf("template", "edits")) { "invalid expansion fields" }
        val name = expansion["template"]
        require(name is JsonPrimitive && name.isString && name.asString.isNotEmpty()) { "invalid template name" }
        var result = requireNotNull(templates[name.asString]) { "unknown template ${name.asString}" }.deepCopy()
        require(expansion["edits"].isJsonArray) { "edits must be an array" }
        for (entry in expansion.getAsJsonArray("edits")) {
            require(entry.isJsonObject) { "edit must be an object" }
            val edit = entry.asJsonObject
            require(edit.keySet().all { it in setOf("op", "path", "value") }) { "unknown edit field" }
            val operation = edit["op"]
            require(operation == null || operation is JsonPrimitive && operation.isString) { "invalid operation" }
            val op = operation?.asString ?: "replace"
            require(op in setOf("replace", "append", "remove")) { "unsupported edit $op" }
            require(edit.has("value") == (op != "remove")) { "invalid edit value" }
            require(edit["path"]?.isJsonArray == true) { "path must be an array" }
            val path = edit.getAsJsonArray("path")
            for (segment in path) {
                if (segment.isJsonArray || segment is JsonPrimitive && segment.isString && segment.asString == "*") {
                    require(op == "replace") { "selections are replacement-only" }
                    if (segment.isJsonArray) {
                        val indices = segment.asJsonArray.map(::index)
                        require(indices.isNotEmpty() && indices.distinct().size == indices.size) { "invalid index selection" }
                    }
                } else if (segment is JsonPrimitive && segment.isString) {
                    require(segment.asString.isNotEmpty()) { "empty object key" }
                } else index(segment)
            }
            if (path.isEmpty) {
                require(op == "replace") { "cannot append/remove root" }
                result = edit["value"].deepCopy()
                continue
            }
            fun walk(node: JsonElement, depth: Int) {
                val segment = path[depth]
                val keys: List<JsonElement> = when {
                    segment.isJsonArray -> { require(node.isJsonArray) { "selection requires array" }; segment.asJsonArray.toList() }
                    segment is JsonPrimitive && segment.isString && segment.asString == "*" -> {
                        require(node.isJsonArray) { "wildcard requires array" }
                        (0 until node.asJsonArray.size()).map(::JsonPrimitive)
                    }
                    else -> listOf(segment)
                }
                for (key in keys) {
                    val child = child(node, key)
                    if (depth + 1 < path.size()) walk(child, depth + 1)
                    else when (op) {
                        "append" -> { require(child.isJsonArray) { "append requires array" }; child.asJsonArray.add(edit["value"].deepCopy()) }
                        "remove" -> if (node.isJsonArray) node.asJsonArray.remove(index(key)) else node.asJsonObject.remove(key.asString)
                        "replace" -> if (node.isJsonArray) node.asJsonArray.set(index(key), edit["value"].deepCopy()) else node.asJsonObject.add(key.asString, edit["value"].deepCopy())
                    }
                }
            }
            walk(result, 0)
        }
        return result
    }

    private fun index(value: JsonElement): Int {
        require(value is JsonPrimitive && value.isNumber) { "array index must be an integer" }
        val integer = try { value.asBigDecimal.intValueExact() } catch (_: ArithmeticException) { error("array index out of range or fractional") }
        require(integer >= 0) { "negative array index" }
        return integer
    }

    private fun child(parent: JsonElement, key: JsonElement): JsonElement {
        if (parent.isJsonArray) {
            val i = index(key)
            require(i < parent.asJsonArray.size()) { "nonexistent array index $i" }
            return parent.asJsonArray[i]
        }
        require(parent.isJsonObject && key is JsonPrimitive && key.isString) { "object traversal requires string key" }
        return requireNotNull(parent.asJsonObject[key.asString]) { "nonexistent object key ${key.asString}" }
    }
}
