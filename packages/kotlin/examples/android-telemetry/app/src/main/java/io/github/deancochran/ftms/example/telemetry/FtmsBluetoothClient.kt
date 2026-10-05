package io.github.deancochran.ftms.example.telemetry

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.ParcelUuid
import java.util.UUID

/** Example-owned transport. All mutable state and listener calls stay on the main looper. */
@SuppressLint("MissingPermission") // Recheck permissions before operations; contain revocation races.
class FtmsBluetoothClient(private val context: Context, private val listener: Listener) {
    interface Listener {
        fun status(text: String)
        fun devices(found: List<BluetoothDevice>)
        fun packet(bytes: ByteArray)
    }

    private val handler = Handler(Looper.getMainLooper())
    private val sessions = SessionGate()
    private var scanner: BluetoothLeScanner? = null
    private var scanCallback: ScanCallback? = null
    private var gatt: BluetoothGatt? = null
    private var subscribed = false
    private val found = linkedMapOf<String, BluetoothDevice>()
    private val serviceUuid = UUID.fromString("00001826-0000-1000-8000-00805f9b34fb")
    private val dataUuid = UUID.fromString(INDOOR_BIKE_DATA)
    private val cccd = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
    private var deadline: Runnable? = null

    fun scan() {
        close(null)
        if (!permitted()) { listener.status("Bluetooth permission denied"); return }
        try {
            val adapter = context.getSystemService(BluetoothManager::class.java)?.adapter
            if (adapter?.isEnabled != true) { listener.status("Bluetooth is unavailable or off"); return }
            if (Build.VERSION.SDK_INT < 31 && !locationEnabled()) {
                listener.status("Enable system Location for Bluetooth scanning on Android 8–11")
                return
            }
            val activeScanner = adapter.bluetoothLeScanner
                ?: run { listener.status("Bluetooth scanner unavailable"); return }
            val epoch = sessions.next()
            val callback = object : ScanCallback() {
                override fun onScanResult(type: Int, result: ScanResult) {
                    handler.post {
                        if (!sessions.accepts(epoch) || scanCallback !== this) return@post
                        if (!permitted()) { close("Bluetooth permission revoked"); return@post }
                        try {
                            // Bound the list and do not retain addresses outside this foreground scan.
                            if (found.size < 32 || found.containsKey(result.device.address)) {
                                found[result.device.address] = result.device
                                listener.devices(found.values.toList())
                            }
                        } catch (_: SecurityException) { close("Bluetooth permission revoked") }
                    }
                }
                override fun onScanFailed(errorCode: Int) {
                    handler.post {
                        if (sessions.accepts(epoch) && scanCallback === this) {
                            cancelDeadline()
                            stopScan()
                            found.clear()
                            listener.devices(emptyList())
                            listener.status("Scan failed ($errorCode)")
                        }
                    }
                }
            }
            scanner = activeScanner
            scanCallback = callback
            activeScanner.startScan(
                listOf(ScanFilter.Builder().setServiceUuid(ParcelUuid(serviceUuid)).build()),
                ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), callback,
            )
            listener.status("Scanning for FTMS services (10 seconds)")
            armDeadline(10_000) {
                stopScan()
                listener.status("Scan finished; select a device or scan again")
            }
        } catch (_: SecurityException) { close("Bluetooth permission denied") }
          catch (_: IllegalStateException) { close("Bluetooth became unavailable") }
    }

    fun select(device: BluetoothDevice) {
        // Only a device from this scan may be selected; never reconnect from persisted identifiers.
        if (device !in found.values) return
        close(null)
        if (!permitted()) { listener.status("Bluetooth permission denied"); return }
        val epoch = sessions.next()
        listener.status("Connecting to selected device")
        try {
            // API 26 overload delivers GATT callbacks on our main handler, after this call returns.
            gatt = device.connectGatt(context, false, callback(epoch), BluetoothDevice.TRANSPORT_LE,
                BluetoothDevice.PHY_LE_1M_MASK, handler)
            if (gatt == null) { close("Connection could not start"); return }
            armDeadline(12_000) { close("Connection timed out") }
        } catch (_: SecurityException) { close("Bluetooth permission denied") }
          catch (_: IllegalStateException) { close("Bluetooth became unavailable") }
    }

    fun close(message: String? = "Disconnected") {
        sessions.next()
        cancelDeadline()
        stopScan()
        found.clear()
        listener.devices(emptyList())
        subscribed = false
        val old = gatt
        gatt = null // Invalidate callbacks before teardown, even if permissions have been revoked.
        try { old?.disconnect() } catch (_: SecurityException) { }
        try { old?.close() } catch (_: SecurityException) { }
        if (message != null) listener.status(message)
    }

    private fun stopScan() {
        val oldScanner = scanner
        val oldCallback = scanCallback
        scanner = null
        scanCallback = null
        if (oldCallback != null) {
            try { oldScanner?.stopScan(oldCallback) }
            catch (_: SecurityException) { }
            catch (_: IllegalStateException) { }
        }
    }

    private fun permitted() = bluetoothPermissions(Build.VERSION.SDK_INT).all {
        context.checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED
    }

    private fun locationEnabled(): Boolean {
        val manager = context.getSystemService(LocationManager::class.java) ?: return false
        return if (Build.VERSION.SDK_INT >= 28) manager.isLocationEnabled
        else manager.isProviderEnabled(LocationManager.GPS_PROVIDER) || manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
    }

    private fun cancelDeadline() { deadline?.let(handler::removeCallbacks); deadline = null }
    private fun armDeadline(delay: Long, action: () -> Unit) {
        cancelDeadline()
        val epoch = sessions.current
        deadline = Runnable { if (sessions.accepts(epoch)) action() }.also { handler.postDelayed(it, delay) }
    }

    private fun callback(epoch: Long) = object : BluetoothGattCallback() {
        private fun withCurrent(g: BluetoothGatt, action: () -> Unit) {
            if (!sessions.accepts(epoch) || g !== gatt) return
            if (!permitted()) { close("Bluetooth permission revoked"); return }
            try { action() }
            catch (_: SecurityException) { close("Bluetooth permission revoked") }
            catch (_: IllegalStateException) { close("Bluetooth became unavailable") }
        }

        override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) = withCurrent(g) {
            if (status != BluetoothGatt.GATT_SUCCESS || newState == BluetoothProfile.STATE_DISCONNECTED) {
                close("Disconnected (GATT status $status)")
            } else if (newState == BluetoothProfile.STATE_CONNECTED) {
                listener.status("Discovering FTMS services")
                armDeadline(8_000) { close("Service discovery timed out") }
                if (!g.discoverServices()) close("Service discovery could not start")
            }
        }

        override fun onServicesDiscovered(g: BluetoothGatt, status: Int) = withCurrent(g) {
            val characteristic = g.getService(serviceUuid)?.getCharacteristic(dataUuid)
            if (status != BluetoothGatt.GATT_SUCCESS || characteristic == null ||
                characteristic.properties and BluetoothGattCharacteristic.PROPERTY_NOTIFY == 0) {
                close("Indoor Bike notifications unavailable")
                return@withCurrent
            }
            val descriptor = characteristic.getDescriptor(cccd)
                ?: run { close("CCCD missing"); return@withCurrent }
            if (!g.setCharacteristicNotification(characteristic, true)) {
                close("Notification setup failed"); return@withCurrent
            }
            listener.status("Subscribing to read-only telemetry")
            armDeadline(8_000) { close("Subscription timed out") }
            // The only remote write is the notification subscription descriptor, never a characteristic.
            val started = if (Build.VERSION.SDK_INT >= 33) {
                g.writeDescriptor(descriptor, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE) == BluetoothStatusCodes.SUCCESS
            } else {
                @Suppress("DEPRECATION")
                descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                @Suppress("DEPRECATION")
                g.writeDescriptor(descriptor)
            }
            if (!started) close("CCCD subscription failed")
        }

        override fun onDescriptorWrite(g: BluetoothGatt, d: BluetoothGattDescriptor, status: Int) = withCurrent(g) {
            if (d.uuid != cccd || d.characteristic.uuid != dataUuid) return@withCurrent
            if (status != BluetoothGatt.GATT_SUCCESS) { close("Subscription failed ($status)"); return@withCurrent }
            cancelDeadline()
            subscribed = true
            listener.status("Subscribed: read-only telemetry")
        }

        @Deprecated("Legacy callback for API 26–32")
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic) {
            if (Build.VERSION.SDK_INT < 33) {
                @Suppress("DEPRECATION")
                val value = c.value?.copyOf() ?: return
                deliver(g, c, value)
            }
        }
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) {
            deliver(g, c, value.copyOf())
        }
        private fun deliver(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) = withCurrent(g) {
            if (subscribed && c.uuid == dataUuid && c.service.uuid == serviceUuid) listener.packet(value)
        }
    }
}

/** Pure, example-owned generation check. Invalidated on every scan/connection/close. */
class SessionGate {
    var current: Long = 0L
        private set
    fun next(): Long = ++current
    fun accepts(callbackEpoch: Long): Boolean = callbackEpoch == current
}

@SuppressLint("InlinedApi")
fun bluetoothPermissions(api: Int): Array<String> = if (api >= 31) {
    arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
} else arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
