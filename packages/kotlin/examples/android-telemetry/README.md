# Android read-only FTMS telemetry example

This standalone Kotlin Android app is a **foreground-only, read-only** consumer
adapter for Indoor Bike Data. It resolves `io.github.deancochran:ftms:0.2.0` from
Maven Central, with no composite build, local Maven repository or project-source
substitution. The protocol library is unchanged. No Google Play services are used.

## Build and run

Use JDK 17 and Android SDK 35 with build tools accepted by AGP 8.10.1. The project
uses Kotlin 2.2.0 and the package-owned Gradle 8.14.3 wrapper. Run from
**`packages/kotlin/`**:

```sh
export ANDROID_HOME=/path/to/android-sdk
./gradlew --no-daemon --max-workers=2 -p examples/android-telemetry \
  :app:testDebugUnitTest :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug

# Start a dedicated emulator yourself, then select its exact adb serial.
adb devices
bash examples/android-telemetry/verify-emulator.sh emulator-5554
```

The verifier refuses non-emulator targets, builds the app/tests, installs only
this sample and its test APK, clears this sample's data for permission-free tests,
and requires all four instrumentation tests to pass. It does not scan, grant BLE
permissions or connect to equipment. It requires `adb` and Python 3; set `ADB` to
an absolute adb executable if necessary. The report is retained at
`app/build/reports/emulator/instrumentation.txt` under this example.

For a manual emulator demo after installation:

```sh
adb -s emulator-5554 shell am start -n \
  io.github.deancochran.ftms.example.telemetry/.MainActivity
```

Tap **Show synthetic demo**. The display is explicitly marked synthetic and shows
10 m/s, 90 rpm and 200 W. No permission request or Bluetooth operation is needed.
Physical-device installation and BLE interaction are separate operator actions,
not part of this verification script.

## BLE behavior and limitations

- Tap **Scan**, grant permissions, then select a particular discovered device to
  connect. Nothing scans or connects automatically on startup or resume.
- Android 12+ uses Nearby Devices permissions. Android 8–11 requires foreground
  fine-location permission and system Location enabled for scanning. Location is
  not collected. `neverForLocation` is declared on Android 12+, which can filter
  some advertisements.
- Only devices advertising the FTMS service UUID are listed. Some equipment may
  omit it from advertising and therefore not appear. Scan is bounded to ten
  seconds and 32 entries. Names appear only in the transient selection UI, not
  logs or persistence. Hardware addresses remain internal in-memory scan keys.
- Connection has a twelve-second deadline; discovery and subscription each have
  eight seconds. Scan and GATT callbacks are guarded by session generations and
  delivered on the main looper. There are no automatic reconnects.
- The sole remote write is the standard Client Characteristic Configuration
  Descriptor (CCCD), to enable Indoor Bike notifications. There are no
  characteristic writes, Control Point commands, or control ownership requests.
- Demo, format change, disconnect and `onStop` cancel the transport session.
  Stop/resume, errors and new sessions clear displayed values. Live values expire
  after five seconds without another packet. This is deliberately not a
  background workout recorder.
- Speed, cadence, power and resistance are displayed only when present in the
  current packet. Missing values are omitted, not reused from previous packets.
- Default resistance layout is `UINT8_WHOLE`; the UI offers an explicit
  `SINT16_TENTHS` choice. This affects field alignment as well as resistance units.
  Select according to documented equipment behavior, never inferred from bytes.
- Each notification is an individual packet. More Data is labelled; neither it
  nor a final packet is claimed to be a complete assembled record. Truncated,
  trailing-byte, reserved-flag, invalid and unsupported inputs clear the display.
- No Internet permission, background service, equipment-control policy or BLE
  framework is added to the protocol package.

## Verification evidence

Local verification on 2026-10-05:

- **11 host unit tests passed**, zero failures/skips.
- Debug application and instrumentation APKs built.
- **Four instrumentation tests executed and passed on API 35 x86_64**, using a
  dedicated Android emulator. They cover public-artifact decoding, actual demo UI
  clicks without permissions, disconnect/format clearing, stop/resume behavior,
  and empty/denied permission-result handling.
- Lint completed with zero errors. Warnings remain for the intentionally retained
  SDK/test-tool baseline, API-versioned manifest attributes, backup metadata,
  example icon and English-only UI. This is not a store-ready application.
- The resolved FTMS JAR SHA-256 matched Maven Central:
  `c86a043bb9be0f52500156d26dfc31829db49d824c068bb725118d3dd0b61aa8`.

API 26 is the build minimum, **not an executed-device claim**. These tests do not
exercise a real Bluetooth stack, discovery, notification subscription, permission
revocation during GATT operations or OEM lifecycle quirks. The session-generation
unit test is not a simulated Android GATT test. No real equipment, Karoo firmware,
recording integration or Bluetooth qualification has been verified.

Android references: [permissions](https://developer.android.com/develop/connectivity/bluetooth/bt-permissions),
[GATT data transfer](https://developer.android.com/develop/connectivity/bluetooth/ble/transfer-ble-data),
[background lifecycle](https://developer.android.com/develop/connectivity/bluetooth/ble/background).
