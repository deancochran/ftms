package io.github.deancochran.ftms.legacy

import com.google.gson.Gson
import com.google.gson.JsonElement

internal val gson: Gson = com.google.gson.GsonBuilder().serializeNulls().setPrettyPrinting().create()
internal fun json(value: Any?): JsonElement = gson.toJsonTree(value)
internal fun demand(condition: Boolean, message: String) { if (!condition) throw AssertionError(message) }

/** Exact JSON structure; JSON numbers compare numerically, never as strings/booleans. */
internal fun exact(actual: JsonElement, expected: JsonElement, path: String = "value") {
    compare(actual, expected, path, false)
}

/** Recursive object subset, but arrays always have full length and positional order. */
internal fun subset(actual: JsonElement, expected: JsonElement, path: String = "value") {
    compare(actual, expected, path, true)
}

private fun compare(actual: JsonElement, expected: JsonElement, path: String, subset: Boolean) {
    when {
        expected.isJsonObject -> {
            demand(actual.isJsonObject, "$path: expected object, got $actual")
            val a = actual.asJsonObject; val e = expected.asJsonObject
            if (!subset) demand(a.keySet() == e.keySet(), "$path: keys ${a.keySet()} != ${e.keySet()}")
            for ((key, value) in e.entrySet()) {
                demand(a.has(key), "$path.$key: missing")
                compare(a[key], value, "$path.$key", subset)
            }
        }
        expected.isJsonArray -> {
            demand(actual.isJsonArray, "$path: expected array")
            demand(actual.asJsonArray.size() == expected.asJsonArray.size(), "$path: array length differs")
            expected.asJsonArray.forEachIndexed { i, value -> compare(actual.asJsonArray[i], value, "$path[$i]", subset) }
        }
        else -> demand(actual == expected, "$path: $actual != $expected")
    }
}

internal fun metrics(actual: JsonElement, expected: JsonElement) {
    demand(actual.isJsonObject && expected.isJsonObject, "metrics must be objects")
    for ((key, value) in expected.asJsonObject.entrySet()) {
        demand(actual.asJsonObject.has(key), "metric $key: missing")
        val got = actual.asJsonObject[key]
        if (value.isJsonPrimitive && value.asJsonPrimitive.isNumber) {
            demand(got.isJsonPrimitive && got.asJsonPrimitive.isNumber, "metric $key: expected number")
            val number = got.asDouble
            demand(number.isFinite() && kotlin.math.abs(number - value.asDouble) < 0.005,
                "metric $key: $got outside strict <0.005 tolerance from $value")
        } else exact(got, value, "metric $key")
    }
}
