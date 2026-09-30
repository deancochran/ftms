package example

import io.github.deancochran.ftms.FeatureCodec
import io.github.deancochran.ftms.Features

fun main() {
    val literal = byteArrayOf(-1, -1, -1, -1, 0, 0, 0, -128)
    val value = FeatureCodec.decode(literal)
    check(value.machine == 0xffffffffL && value.target == 0x80000000L)
    check(FeatureCodec.encode(Features(0xffffffffL, 0x80000000L)).contentEquals(literal))
    check(runCatching { FeatureCodec.decode(byteArrayOf()) }.exceptionOrNull() is IllegalArgumentException)
    println("Kotlin isolated artifact consumer passed")
}
