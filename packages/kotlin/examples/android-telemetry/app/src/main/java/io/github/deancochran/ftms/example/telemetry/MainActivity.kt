package io.github.deancochran.ftms.example.telemetry

import android.bluetooth.BluetoothDevice
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.*

/** Foreground-only example, not a ride recorder or background connection service. */
class MainActivity : android.app.Activity(), FtmsBluetoothClient.Listener {
    private lateinit var telemetry: TextView
    private lateinit var devices: LinearLayout
    private lateinit var client: FtmsBluetoothClient
    private var presenter = TelemetryPresenter()
    private var signedTenths = false
    private var foreground = false
    private val handler = Handler(Looper.getMainLooper())
    private val expire = Runnable { status("No recent packet (5 seconds); telemetry cleared") }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        client = FtmsBluetoothClient(this, this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }
        // Target SDK 35 is edge-to-edge. Keep controls clear of status/navigation bars.
        root.setOnApplyWindowInsetsListener { view, insets ->
            @Suppress("DEPRECATION")
            view.setPadding(24 + insets.systemWindowInsetLeft, 24 + insets.systemWindowInsetTop,
                24 + insets.systemWindowInsetRight, 24 + insets.systemWindowInsetBottom)
            insets
        }
        fun button(label: String, action: () -> Unit) = Button(this).apply {
            text = label
            setOnClickListener { action() }
            root.addView(this)
        }
        telemetry = TextView(this).apply { tag = "telemetry" }
        devices = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(TextView(this).apply { text = "FTMS Indoor Bike: foreground, read-only" })
        button("Show synthetic demo") {
            client.close(null)
            handler.removeCallbacks(expire)
            presenter.decode(byteArrayOf(0x44, 0, 0x10, 0x0e, 0xb4.toByte(), 0, 0xc8.toByte(), 0), synthetic = true)
            render()
        }
        button("Scan for FTMS bikes") { requestThenScan() }
        val formatButton = button("Resistance: UINT8 whole (tap for SINT16 tenths)") {}
        formatButton.setOnClickListener {
            client.close(null)
            signedTenths = !signedTenths
            presenter = TelemetryPresenter(selectedFormat(signedTenths))
            formatButton.text = if (signedTenths) "Resistance: SINT16 tenths (tap for UINT8 whole)"
                else "Resistance: UINT8 whole (tap for SINT16 tenths)"
            status("Format changed; choose scan or demo")
        }
        button("Disconnect") { client.close() }
        root.addView(telemetry)
        root.addView(devices)
        setContentView(ScrollView(this).apply { addView(root) })
        status("Choose synthetic demo or explicitly scan")
    }

    private fun permissionsGranted() = bluetoothPermissions(Build.VERSION.SDK_INT).all {
        checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED
    }
    private fun requestThenScan() {
        if (!foreground) return
        if (!permissionsGranted()) requestPermissions(bluetoothPermissions(Build.VERSION.SDK_INT), 4)
        else beginScan()
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grants: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grants)
        if (requestCode != 4) return
        // Never resume a scan from a permission result after the Activity has stopped.
        if (foreground && grants.isNotEmpty() && permissionsGranted()) beginScan()
        else status("Permission denied or app stopped; tap Scan to try again")
    }
    private fun beginScan() { status("Scanning; previous telemetry cleared"); client.scan() }

    override fun status(text: String) {
        handler.removeCallbacks(expire)
        presenter.clear(text)
        render()
    }
    override fun devices(found: List<BluetoothDevice>) {
        devices.removeAllViews()
        found.forEachIndexed { index, device ->
            devices.addView(Button(this).apply {
                // A transient name/ordinal aids selection; hardware addresses are never displayed.
                @Suppress("MissingPermission")
                val label = try { "${index + 1}: ${device.name ?: "Unnamed FTMS device"}" }
                    catch (_: SecurityException) { "FTMS device ${index + 1}" }
                text = "Connect: $label"
                setOnClickListener { if (this@MainActivity.foreground) { status("Connecting; previous telemetry cleared"); client.select(device) } }
            })
        }
    }
    override fun packet(bytes: ByteArray) {
        if (!foreground) return
        presenter.decode(bytes)
        render()
        handler.removeCallbacks(expire)
        handler.postDelayed(expire, 5_000)
    }
    private fun render() { telemetry.text = presenter.state.text() }
    override fun onStart() { super.onStart(); foreground = true }
    override fun onStop() {
        foreground = false
        client.close(null)
        status("Stopped; previous telemetry cleared. Choose scan or demo again.")
        super.onStop()
    }
}
