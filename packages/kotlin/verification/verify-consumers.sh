#!/usr/bin/env bash
# Resolve only the requested Maven repository/version, never project sources.
set -euo pipefail
package=$(cd "$(dirname "$0")/.." && pwd)
repository=${1:?Maven repository path or HTTPS URL required}
version=${2:?Exact FTMS version required}
cd "$package"
for consumer in java-consumer kotlin-consumer; do
    ./gradlew --no-daemon --refresh-dependencies -p "verification/$consumer" \
        "-PftmsRepository=$repository" "-PftmsVersion=$version" clean run
done
if [[ -z "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}" ]]; then
    echo 'Android SDK is required for the complete release-readiness gate.' >&2
    exit 1
fi
./gradlew --no-daemon --refresh-dependencies -p verification/android-consumer \
    "-PftmsRepository=$repository" "-PftmsVersion=$version" clean assembleDebug
