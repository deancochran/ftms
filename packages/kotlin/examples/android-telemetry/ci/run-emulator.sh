#!/usr/bin/env bash
# Linux CI/local runner: boot a private AVD; never attach to an existing device.
set -euo pipefail
example=$(cd "$(dirname "$0")/.." && pwd)
api=${1:?Usage: bash ci/run-emulator.sh 26|35}
[[ "$api" == 26 || "$api" == 35 ]] || { echo 'Unsupported verification API.' >&2; exit 1; }
sdk=${ANDROID_HOME:?ANDROID_HOME must name a prepared SDK}
export ADB="$sdk/platform-tools/adb"
serial=emulator-5580
report="$example/app/build/reports/emulator"
mkdir -p "$report"
# Avoid attributing a previous local run's success or diagnostics to this attempt.
for file in instrumentation.txt environment.txt emulator.log logcat.txt; do
    : > "$report/$file"
done
# adb starts its local server if necessary, but this script never selects another device.
devices=$(timeout --kill-after=5s 15 "$ADB" devices)
if grep -q "^$serial[[:space:]]" <<< "$devices"; then
    echo "Refusing to replace existing $serial" >&2
    exit 1
fi
temp=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp/opencode}}/ftms-avd.XXXXXX")
export ANDROID_AVD_HOME="$temp/avd"
mkdir -p "$ANDROID_AVD_HOME"
emulator_pid=
cleanup() {
    result=$?
    trap - EXIT
    if [[ -n "$emulator_pid" ]]; then
        if [[ $result -ne 0 ]]; then
            # Only this synthetic test AVD is addressed. No physical-device logs are collected.
            timeout --kill-after=5s 10 "$ADB" -s "$serial" logcat -d -t 500 > "$report/logcat.txt" 2>&1 || true
        fi
        kill "$emulator_pid" 2>/dev/null || true
        # Bound graceful shutdown as well as boot; a stuck emulator must not hang cleanup.
        timeout --kill-after=5s 15 tail --pid="$emulator_pid" -f /dev/null 2>/dev/null || kill -KILL "$emulator_pid" 2>/dev/null || true
        wait "$emulator_pid" 2>/dev/null || true
    fi
    # Delete only the fresh, script-owned temporary AVD.
    rm -rf -- "$temp"
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
printf 'no\n' | timeout --kill-after=5s 120 "$sdk/cmdline-tools/latest/bin/avdmanager" create avd \
    --name ftms-ci --package "system-images;android-$api;google_apis;x86_64" --device pixel_2
"$sdk/emulator/emulator" -avd ftms-ci -port 5580 -no-window -no-audio \
    -no-snapshot -no-boot-anim -gpu swiftshader_indirect -memory 2048 -cores 2 \
    > "$report/emulator.log" 2>&1 &
emulator_pid=$!
# Bound both transport availability and Android boot completion. Emulator exit is a failure.
echo "Waiting for API $api emulator transport"
timeout --kill-after=5s 180 "$ADB" -s "$serial" wait-for-device
echo "Waiting for Android boot completion"
deadline=$((SECONDS + 180))
until [[ "$(timeout --kill-after=5s 10 "$ADB" -s "$serial" shell getprop sys.boot_completed | tr -d '\r')" == 1 ]]; do
    kill -0 "$emulator_pid" 2>/dev/null || { echo 'Emulator exited during boot.' >&2; exit 1; }
    (( SECONDS < deadline )) || { echo 'Android boot timed out.' >&2; exit 1; }
    sleep 2
done
echo "Checking booted runtime identity"
actual_api=$(timeout --kill-after=5s 30 "$ADB" -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
[[ "$actual_api" == "$api" ]] || { echo "Wrong runtime API: $actual_api" >&2; exit 1; }
{
    echo "Requested/executed API: $api/$actual_api"
    timeout --kill-after=5s 10 "$sdk/emulator/emulator" -version
    timeout --kill-after=5s 30 "$ADB" -s "$serial" shell getprop ro.build.fingerprint
    java -version 2>&1
} > "$report/environment.txt"
timeout --kill-after=5s 30 "$ADB" -s "$serial" shell input keyevent 82
bash "$example/verify-emulator.sh" "$serial" --skip-build
