package io.github.deancochran.ftms.example.telemetry

import android.content.pm.PackageManager
import android.os.Build
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import io.github.deancochran.ftms.measurement.MeasurementDecodeResult
import io.github.deancochran.ftms.measurement.MeasurementReader
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class PublicArtifactInstrumentationTest {
    private fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup) {
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) }
    } else emptyList()
    private fun click(activity: MainActivity, prefix: String) {
        descendants(activity.window.decorView).filterIsInstance<Button>()
            .single { it.text.startsWith(prefix) }.performClick()
    }
    private fun text(activity: MainActivity) = activity.window.decorView
        .findViewWithTag<TextView>("telemetry").text.toString()
    private fun assertPermissionsDenied() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        bluetoothPermissions(Build.VERSION.SDK_INT).forEach {
            assertNotEquals("Tests require a fresh install with no Bluetooth/location grants", PackageManager.PERMISSION_GRANTED, context.checkSelfPermission(it))
        }
    }

    @Test fun publicMavenArtifactDecodesOnAndroid() {
        val decoded = MeasurementReader.decode(UUID.fromString(INDOOR_BIKE_DATA), byteArrayOf(0, 0, 0x10, 0x0e))
            as MeasurementDecodeResult.Decoded
        assertEquals(10.0, decoded.measurement.speedMps!!, 0.0)
        assertFalse(decoded.measurement.raw.truncated)
        val presenter = TelemetryPresenter()
        presenter.decode(byteArrayOf(0, 0, 0x10, 0x0e))
        assertNull(presenter.decode(byteArrayOf(0x40, 0, 0x10, 0x0e)).speed)
    }

    @Test fun demoRunsWithoutBluetoothAndDisconnectClearsIt() {
        assertPermissionsDenied()
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                click(activity, "Show synthetic")
                assertTrue(text(activity).contains("Synthetic demo (no Bluetooth)"))
                assertTrue(text(activity).contains("Speed 10.00 m/s"))
                assertTrue(text(activity).contains("Cadence 90.0 rpm"))
                assertTrue(text(activity).contains("Power 200 W"))
                assertPermissionsDenied()
                click(activity, "Disconnect")
                assertFalse(text(activity).contains("Speed"))
            }
        }
    }

    @Test fun stopAndResumeNeverRestoresStaleValues() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { click(it, "Show synthetic") }
            scenario.moveToState(Lifecycle.State.CREATED)
            scenario.moveToState(Lifecycle.State.RESUMED)
            scenario.onActivity { activity ->
                assertTrue(text(activity).contains("Stopped"))
                assertFalse(text(activity).contains("Speed"))
                click(activity, "Show synthetic")
                click(activity, "Resistance:")
                assertTrue(text(activity).contains("Format changed"))
                assertFalse(text(activity).contains("Power"))
            }
        }
    }

    @Test fun missingAndEmptyPermissionResultsDoNotStartScanning() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                activity.onRequestPermissionsResult(4, emptyArray(), intArrayOf())
                assertTrue(text(activity).contains("Permission denied"))
                assertPermissionsDenied()
            }
        }
    }
}
