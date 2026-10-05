#!/usr/bin/env bash
# Explicitly selected emulator only. Clears this sample's data, never grants BLE permissions.
set -euo pipefail
example=$(cd "$(dirname "$0")" && pwd)
serial=${1:?Usage: bash verify-emulator.sh emulator-SERIAL}
mode=${2:-build}
[[ "$mode" == build || "$mode" == --skip-build ]] || { echo 'Unknown build mode.' >&2; exit 1; }
[[ "$serial" == emulator-* ]] || { echo 'Refusing a non-emulator serial.' >&2; exit 1; }
adb_bin=${ADB:-adb}
[[ "$(timeout --kill-after=5s 15 "$adb_bin" -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || {
    echo 'The selected target is not a verified emulator.' >&2; exit 1;
}
if [[ "$mode" == build ]]; then
    "$example/../../gradlew" --no-daemon --max-workers=2 -p "$example" \
        :app:testDebugUnitTest :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug
fi
timeout --kill-after=5s 60 "$adb_bin" -s "$serial" install -r "$example/app/build/outputs/apk/debug/app-debug.apk"
timeout --kill-after=5s 60 "$adb_bin" -s "$serial" install -r "$example/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"
package=io.github.deancochran.ftms.example.telemetry
timeout --kill-after=5s 15 "$adb_bin" -s "$serial" shell pm clear "$package" | grep -Fx Success
mkdir -p "$example/app/build/reports/emulator"
report="$example/app/build/reports/emulator/instrumentation.txt"
timeout --kill-after=5s 180 "$adb_bin" -s "$serial" shell am instrument -w -r \
    "$package.test/androidx.test.runner.AndroidJUnitRunner" | tee "$report"
# adb may exit zero when instrumentation fails. Require every named scenario, without skips.
python3 "$example/ci/check_instrumentation.py" "$report"
