#!/usr/bin/env bash
# Host and artifact checks only; never connects to equipment or publishes remotely.
set -euo pipefail
package=$(cd "$(dirname "$0")/.." && pwd)
cd "$package"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s publishing -p 'test_*.py'
./gradlew --no-daemon clean check publishMavenJavaPublicationToLocalVerificationRepository
repository="$package/build/local-maven"
version=$(PYTHONDONTWRITEBYTECODE=1 python3 -c 'from publishing.publish import publication; print(publication()[0])')
bash verification/verify-consumers.sh "$repository" "$version"
echo 'Host tests and all three artifact-consumer builds passed.'
echo 'No emulator, Bluetooth, or remote publication check was performed.'
