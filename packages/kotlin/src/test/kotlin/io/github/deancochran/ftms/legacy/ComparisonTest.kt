package io.github.deancochran.ftms.legacy

import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class ComparisonTest {
    @Test fun metricToleranceIsStrictAndFinite() {
        metrics(json(mapOf("x" to 0.004999)), json(mapOf("x" to 0)))
        for (bad in listOf(0.005, -0.005, Double.NaN, Double.POSITIVE_INFINITY)) {
            val value = com.google.gson.JsonObject().apply { addProperty("x", bad) }
            assertThrows(AssertionError::class.java) { metrics(value, json(mapOf("x" to 0))) }
        }
        for (bad in listOf(json(mapOf("x" to "0")), json(mapOf("x" to false)), json(emptyMap<String, Int>()))) {
            assertThrows(AssertionError::class.java) { metrics(bad, json(mapOf("x" to 0))) }
        }
    }
    @Test fun subsetRequiresNullKeysAndFullOrderedArrays() {
        subset(json(listOf(mapOf("x" to 1, "extra" to 2))), json(listOf(mapOf("x" to 1))))
        for ((a, e) in listOf(
            json(listOf(1, 2)) to json(listOf(1)),
            json(listOf(2, 1)) to json(listOf(1, 2)),
            json(emptyMap<String, Int>()) to com.google.gson.JsonParser.parseString("{\"x\":null}"),
            json(mapOf("x" to 0)) to com.google.gson.JsonParser.parseString("{\"x\":null}")
        )) assertThrows(AssertionError::class.java) { subset(a, e) }
    }
    @Test fun exactRejectsExtraKeysAndTypeCoercion() {
        assertThrows(AssertionError::class.java) { exact(json(mapOf("a" to 1, "b" to 2)), json(mapOf("a" to 1))) }
        assertThrows(AssertionError::class.java) { exact(json(true), json(1)) }
        assertThrows(AssertionError::class.java) { exact(json("1"), json(1)) }
        exact(json(1.0), json(1))
    }
}
