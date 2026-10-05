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
permissions or connect to equipment. It requires `adb`, Python 3 and GNU `timeout`
(Linux, or GNU coreutils on other hosts); set `ADB` to
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

## Continuous verification

The reusable [Kotlin workflow](../../../../.github/workflows/native-kotlin.yml)
has an Android example matrix for **API 26 and API 35**. Each lane:

1. Tests the instrumentation-report checker, including failure/skip/partial-run cases.
2. Builds the application and test APKs, runs host unit tests and lint.
3. Boots a private, accelerated x86_64 emulator with bounded startup/shutdown.
4. Executes all four named instrumentation scenarios with a three-minute timeout.
5. Uploads host test/lint reports, instrumentation output and emulator/environment
   logs for 14 days, including when an earlier step fails. Failure-only logcat is
   collected from the synthetic emulator, never a physical device.

Each API lane is independent (`fail-fast: false`). A failure propagates through
the reusable Kotlin job to the existing **CI summary** gate. Relevant package
changes already select Kotlin verification; no new required-check name needs to
be configured. No physical BLE access, new secrets or release permission is used.

To reproduce a CI lane on Linux, first build as above and install the matching
SDK image, then run:

```sh
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
  "system-images;android-26;google_apis;x86_64"
bash examples/android-telemetry/ci/run-emulator.sh 26
# Repeat with image android-35 and argument 35 for the other lane.
python3 -m unittest discover -s examples/android-telemetry/ci -p 'test_*.py' -v
```

The runner refuses an existing `emulator-5580`, creates and removes only its own
temporary AVD, checks the actual API level, and shuts down its emulator on exit.
It uses the already built APKs through `verify-emulator.sh SERIAL --skip-build`;
missing artifacts fail rather than skip. `RUNNER_TEMP` can select a temporary
directory with sufficient disk space. The standalone verifier still builds by
default. Test names are explicitly accounted for in `ci/check_instrumentation.py`;
update that list and the checker tests when adding/removing runtime scenarios.

## Verification evidence

Local verification on 2026-10-05:

- **11 host unit tests passed**, zero failures/skips.
- Debug application and instrumentation APKs built.
- **Initial local CI-runner executions passed four instrumentation tests on each
  of API 26 and API 35 x86_64**. They cover public-artifact decoding, actual demo UI
  clicks without permissions, disconnect/format clearing, stop/resume behavior,
  and empty/denied permission-result handling.
- **11 report-accounting tests passed**, covering incomplete/empty runs, failures,
  skips, duplicate/unexpected scenarios and false-success summaries.
- Lint completed with zero errors. Warnings remain for the intentionally retained
  SDK/test-tool baseline, API-versioned manifest attributes, backup metadata,
  example icon and English-only UI. This is not a store-ready application.
- The resolved FTMS JAR SHA-256 matched Maven Central:
  `c86a043bb9be0f52500156d26dfc31829db49d824c068bb725118d3dd0b61aa8`.

Repeated API 35 runs during CI hardening subsequently encountered emulator boot
timeouts and a lost transport mid-instrumentation, with QEMU thread-hang messages
on a memory-pressured host. Those attempts failed and retained diagnostics; they
were not skipped or counted as passes. The hardened runner's complete API 35
rerun and the GitHub-hosted workflow execution remain to be verified. No retry
policy hides emulator failures.

API 26 is now emulator-executed, **not a physical-device claim**. These tests do not
exercise a real Bluetooth stack, discovery, notification subscription, the full
permission-grant/Location-services flow, permission revocation during GATT
operations or OEM lifecycle quirks. The session-generation
unit test is not a simulated Android GATT test. No real equipment, Karoo firmware,
recording integration or Bluetooth qualification has been verified.

Android references: [permissions](https://developer.android.com/develop/connectivity/bluetooth/bt-permissions),
[GATT data transfer](https://developer.android.com/develop/connectivity/bluetooth/ble/transfer-ble-data),
[background lifecycle](https://developer.android.com/develop/connectivity/bluetooth/ble/background).
