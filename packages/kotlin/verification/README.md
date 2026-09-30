# Isolated artifact consumers

These are independent builds, not Gradle subprojects or composite builds. They
resolve `io.github.deancochran:ftms:0.1.0` from an explicitly supplied local Maven
repository. No project-source dependency, Node, native compiler, or Swift is used.

After the package publishes its local verification artifact, run from the package:

```sh
./gradlew publishMavenJavaPublicationToLocalVerificationRepository
./gradlew -p verification/java-consumer -PftmsRepository="$PWD/build/local-maven" run
./gradlew -p verification/kotlin-consumer -PftmsRepository="$PWD/build/local-maven" run
ANDROID_HOME=/path/to/sdk ./gradlew -p verification/android-consumer \
  -PftmsRepository="$PWD/build/local-maven" assembleDebug
```

The Android consumer is an offline application with no Bluetooth permissions. An
APK build establishes Android packaging/compilation, not runtime or device-control
evidence. Its proposed baseline is Android API 26 with compile/target API 35,
AGP 8.10.1, and Java 17. Record actual verification before claiming support.
