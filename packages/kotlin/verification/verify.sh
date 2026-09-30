#!/usr/bin/env bash
# Host and artifact checks only; never connects to equipment or publishes remotely.
set -euo pipefail
package=$(cd "$(dirname "$0")/.." && pwd)
cd "$package"
./gradlew --no-daemon clean check publishMavenJavaPublicationToLocalVerificationRepository
repository="$package/build/local-maven"
for consumer in java-consumer kotlin-consumer; do
    ./gradlew --no-daemon --refresh-dependencies -p "verification/$consumer" \
        "-PftmsRepository=$repository" clean run
done
if [[ -z "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}" ]]; then
    echo 'Android SDK is required for the complete release-readiness gate.' >&2
    exit 1
fi
./gradlew --no-daemon --refresh-dependencies -p verification/android-consumer \
    "-PftmsRepository=$repository" clean assembleDebug
echo 'Host tests and all three artifact-consumer builds passed.'
echo 'No emulator, Bluetooth, or remote publication check was performed.'
