package io.github.deancochran.ftms.capability

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

public class CapabilityOwnershipAndRangeTest {
    private fun uuid(short: String): String = "0000${short}00001000800000805f9b34fb"
    private fun evidence(short: String, properties: Int, vararg bytes: Int): CharacteristicEvidence =
        CharacteristicEvidence(uuid(short), properties, if (bytes.isEmpty()) ReadState.NOT_ATTEMPTED else ReadState.SUCCESS,
            readBytes = bytes.map(Int::toByte).toByteArray())

    @Test public fun byteOwnershipIncludesJvmVisibleInternalAccessors(): Unit {
        val bytes = byteArrayOf(1, 0, 0, 0, 4, 0, 0, 0)
        val characteristic = CharacteristicEvidence(uuid("2acc"), 2, ReadState.SUCCESS, readBytes = bytes)
        val expected = bytes.copyOf()
        bytes.fill(0)
        characteristic.readBytes().fill(0)
        // A Java consumer can call internal methods; Kotlin visibility alone is insufficient.
        val accessors = CharacteristicEvidence::class.java.methods.filter {
            it.parameterCount == 0 && it.returnType == ByteArray::class.java
        }
        assertTrue(accessors.any { it.name.startsWith("bytesInternal") })
        for (accessor in accessors) (accessor.invoke(characteristic) as ByteArray).fill(0)
        assertArrayEquals(expected, characteristic.readBytes())
        val source = mutableListOf(characteristic)
        val snapshot = CapabilitySnapshot(DiscoveryState.COMPLETE, ServiceScope.PRESENT, 7, source)
        source.clear()
        assertEquals(1, snapshot.characteristics.size)
        assertThrows(UnsupportedOperationException::class.java) { (snapshot.characteristics as MutableList).clear() }
        val report = FtmsCapabilityEvaluator.evaluate(snapshot)
        assertEquals(1L, report.feature.machineRaw)
        assertEquals(4L, report.feature.targetRaw)
        assertEquals(8, report.observations.single().readSize)
        for (list in listOf(report.presence, report.ranges, report.operations, report.observations, report.diagnostics)) {
            assertThrows(UnsupportedOperationException::class.java) { (list as MutableList).clear() }
        }
    }

    private fun resistanceSnapshot(bytes: IntArray, target: Int = 4): CapabilitySnapshot = CapabilitySnapshot(
        DiscoveryState.COMPLETE, ServiceScope.PRESENT, 0,
        listOf(evidence("2acc", 2, 0, 0, 0, 0, target, 0, 0, 0), evidence("2ad9", 0x28),
            evidence("2ada", 0x10), evidence("2ad6", 2, *bytes)),
        C7Evidence(TruthValue.FALSE, TruthValue.UNKNOWN)
    )
    private val signed = RangeFormatOptions(ResistanceRangeFormat.SINT16_TENTHS)

    @Test public fun explicitSignedTenthsPreservesSignedBoundsAndUnsignedIncrement(): Unit {
        val snapshot = resistanceSnapshot(intArrayOf(0, 0x80, 0xff, 0x7f, 0xff, 0xff))
        val report = FtmsCapabilityEvaluator.evaluate(snapshot, signed)
        val range = report.ranges[2]
        assertEquals(DecodeState.VALID, range.decode)
        val value = requireNotNull(range.value)
        assertEquals(RangeKind.RESISTANCE, value.kind)
        assertEquals(-32768, value.minimum)
        assertEquals(32767, value.maximum)
        assertEquals(65535, value.increment)
        assertEquals(10, value.scaleDivisor)
        assertEquals("level", value.unit)
        assertEquals(Declaration.SUPPORTED, report.operations[4].declaration)
        assertEquals(Prerequisite.SATISFIED, report.operations[4].prerequisite)
        assertEquals(0, report.operations[4].reasons)
        assertTrue(report.diagnostics.isEmpty())
        val default = FtmsCapabilityEvaluator.evaluate(snapshot)
        assertEquals(DecodeState.MALFORMED, default.ranges[2].decode)
        assertEquals(Prerequisite.INCONSISTENT, default.operations[4].prerequisite)
        assertEquals(512, default.operations[4].reasons)
    }

    @Test public fun signedTenthsRequiresExactLengthOrderedBoundsAndNonzeroIncrement(): Unit {
        for (bytes in listOf(intArrayOf(1, 10, 1), intArrayOf(0, 0, 1, 0, 1),
            intArrayOf(0, 0, 1, 0, 1, 0, 0), intArrayOf(1, 0, 0, 0, 1, 0), intArrayOf(0, 0, 1, 0, 0, 0))) {
            val report = FtmsCapabilityEvaluator.evaluate(resistanceSnapshot(bytes), signed)
            assertEquals(DecodeState.MALFORMED, report.ranges[2].decode)
            assertNull(report.ranges[2].value)
            assertEquals(Declaration.SUPPORTED, report.operations[4].declaration)
            assertEquals(Prerequisite.INCONSISTENT, report.operations[4].prerequisite)
            assertEquals(512, report.operations[4].reasons)
            assertEquals(listOf(DiagnosticCode.MALFORMED_BYTES), report.diagnostics.map { it.code })
            assertEquals(KnownCharacteristicKind.RESISTANCE_RANGE, report.diagnostics.single().knownKind)
            assertEquals(3, report.diagnostics.single().inputIndex)
        }
        val whole = FtmsCapabilityEvaluator.evaluate(resistanceSnapshot(intArrayOf(1, 10, 1)))
        assertEquals(DecodeState.VALID, whole.ranges[2].decode)
        assertEquals(1, whole.ranges[2].value?.scaleDivisor)
    }

    @Test public fun signedRangeDoesNotInventDeclarationAndEqualNegativeBoundsAreValid(): Unit {
        val report = FtmsCapabilityEvaluator.evaluate(resistanceSnapshot(intArrayOf(0xf6, 0xff, 0xf6, 0xff, 1, 0), 0), signed)
        assertEquals(DecodeState.VALID, report.ranges[2].decode)
        assertEquals(-10, report.ranges[2].value?.minimum)
        assertEquals(-10, report.ranges[2].value?.maximum)
        assertEquals(Declaration.NOT_SUPPORTED, report.operations[4].declaration)
        assertEquals(Prerequisite.NOT_APPLICABLE, report.operations[4].prerequisite)
        assertEquals(0, report.operations[4].reasons)
    }
}
