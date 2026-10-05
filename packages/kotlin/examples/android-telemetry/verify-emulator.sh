#!/usr/bin/env bash
# Explicitly selected emulator only. Clears this sample's data, never grants BLE permissions.
set -euo pipefail
example=$(cd "$(dirname "$0")" && pwd)
serial=${1:?Usage: bash verify-emulator.sh emulator-SERIAL}
[[ "$serial" == emulator-* ]] || { echo 'Refusing a non-emulator serial.' >&2; exit 1; }
adb_bin=${ADB:-adb}
[[ "$("$adb_bin" -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || {
    echo 'The selected target is not a verified emulator.' >&2; exit 1;
}
"$example/../../gradlew" --no-daemon --max-workers=2 -p "$example" \
    :app:testDebugUnitTest :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug
"$adb_bin" -s "$serial" install -r "$example/app/build/outputs/apk/debug/app-debug.apk"
"$adb_bin" -s "$serial" install -r "$example/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"
package=io.github.deancochran.ftms.example.telemetry
"$adb_bin" -s "$serial" shell pm clear "$package" | grep -Fx Success
mkdir -p "$example/app/build/reports/emulator"
report="$example/app/build/reports/emulator/instrumentation.txt"
"$adb_bin" -s "$serial" shell am instrument -w -r \
    "$package.test/androidx.test.runner.AndroidJUnitRunner" | tee "$report"
# adb may exit zero when instrumentation fails. Require all four tests to finish successfully.
python3 - "$report" <<'PY'
from pathlib import Path
import re
import sys
text = Path(sys.argv[1]).read_text()
codes = re.findall(r'^INSTRUMENTATION_STATUS_CODE: (-?\d+)\s*$', text, re.M)
if (codes.count('0') != 4 or codes.count('1') != 4 or set(codes) != {'0', '1'}
        or 'OK (4 tests)' not in text or 'INSTRUMENTATION_CODE: -1' not in text
        or 'INSTRUMENTATION_FAILED' in text):
    raise SystemExit('Android runtime verification failed or had incomplete test accounting')
print('Verified: 4 executed Android tests, zero failures/skips; no BLE access requested.')
PY
