# FTMS Kotlin/JVM

Independent, transport-neutral Kotlin and Java codecs for Bluetooth Fitness
Machine Service 1.0 plus the applicable errata recorded in the repository's
[specification audit](../../docs/specification-audit.md).

Package version: **0.1.0**. Coordinates: `io.github.deancochran:ftms:0.1.0`.
Published on [Maven Central](https://central.sonatype.com/artifact/io.github.deancochran/ftms/0.1.0).
Exact source, signed artifact hashes and public-consumer evidence are recorded in
[released packages](../../docs/released-packages.md).

```kotlin
repositories { mavenCentral() }
dependencies { implementation("io.github.deancochran:ftms:0.1.0") }
```

Releases use the package-owned `VERSION` file and the
[automated GitHub Actions release process](docs/releasing.md). A reviewed version
bump merged into `main` runs verification, signing, Central publication and public
consumer checks without re-entering credentials or setting up a local signing key.

## Scope

- Bidirectional Features and all five Supported Ranges, including range inspection.
- All 21 Control Point requests, raw and named command APIs, and responses.
- Bidirectional Treadmill, Cross Trainer, Step Climber, Stair Climber, Rower and
  Indoor Bike measurement codecs.
- Training Status and Machine Status codecs, with raw diagnostics.
- Static capability evaluation from caller-provided discovery/read evidence,
  including unknown properties, duplicate observations and C.7 evidence.

The library uses `ByteArray` (`byte[]` from Java). Its only intended runtime
dependency is Kotlin's standard library. It contains no Android framework, BLE,
coroutine, connection, permission, retry, control-ownership or cadence policy.
It neither connects to equipment nor grants permission to execute controls.

## Build and verify

Use JDK 17 and the checked-in Gradle 8.14.3 wrapper:

```sh
cd packages/kotlin
./gradlew clean check
./gradlew publishMavenJavaPublicationToLocalVerificationRepository
ANDROID_HOME=/path/to/android-sdk bash verification/verify.sh
```

Kotlin compiler: 2.2.0. JVM bytecode baseline: Java 17. Java 17 is required for
desktop JVM callers; Android consumption is separately checked through D8 with
min SDK 26, compile/target SDK 35 and AGP 8.10.1. No Android SDK is required to
build or test the core. `verification/verify.sh` does require it for the APK gate.

Tests read canonical files directly under `../../shared/`; they do not use copied
fixtures or install another language port. Gson, NetworkNT and JUnit are test-only.
`check` includes the checked-in binary API baseline. Regenerate that baseline with
`apiDump` only after reviewing an intentional public API change.

## Kotlin example

```kotlin
import io.github.deancochran.ftms.ControlCodec
import io.github.deancochran.ftms.ControlCommand
import io.github.deancochran.ftms.FeatureCodec

val bytes = ControlCodec.encodeCommand(ControlCommand.TargetPower(75))
check(bytes.contentEquals(byteArrayOf(0x05, 0x4b, 0x00)))

// Feed bytes obtained by your transport; encoding does not transmit anything.
val response = ControlCodec.decodeResponse(byteArrayOf(0x80.toByte(), 0x05, 0x01))
check(response.requestOpcode == 5 && response.resultCode == 1)

// Unsigned 32-bit Feature words are represented by non-negative Long values.
val feature = FeatureCodec.decode(byteArrayOf(-1, -1, -1, -1, 0, 0, 0, 0))
check(feature.machine == 0xffffffffL)
```

## Java example

```java
import io.github.deancochran.ftms.ControlCodec;
import io.github.deancochran.ftms.ControlCommand;

byte[] bytes = ControlCodec.encodeCommand(new ControlCommand.TargetPower(75));
```

The independent builds in [verification](verification/README.md) resolve the
produced Maven artifact, not project-source dependencies. They also pass against
the public Maven Central release. For local development, add the verification
repository's file URL as a Maven repository and use the same coordinates:

```kotlin
dependencies { implementation("io.github.deancochran:ftms:0.1.0") }
```

## Values, errors and compatibility

Numeric codec values are **raw integer numerators**, not automatically normalized
physical-unit values. Named command properties state their units; ranges include
`scaleDivisor` and `unit`. Measurement indexes are named by `MeasurementField` and
follow the [raw measurement contract](../../shared/conformance/measurements/README.md).
The historical normalized-v1 adapter is test-only, not a second public API.

Measurements preserve separate `present` and `unavailable` masks. An unavailable
sentinel has a zero raw slot plus its unavailable bit; that is not an actual zero
measurement. Check these masks before interpreting a value. `moreData` is retained;
the library does not assemble multiple notifications into a session record.

Invalid fixed layouts/arguments throw `IllegalArgumentException` (foundation
codecs use `FtmsException` with `FtmsError`). Measurement and status payloads retain
their supported malformed/truncated/trailing/unknown evidence; an incomplete
mandatory header is rejected. Encoding rejects invalid widths and non-encodable
diagnostics rather than silently narrowing values. See generated KDoc and shared
contracts for each raw report.

Range, control and measurement format selections are independent and explicit.
Defaults match the shared contracts; alternative resistance widths and legacy
treadmill pace are never inferred from payload length, device name or another
characteristic. Structural range candidates do not prove physical units.

Public command data classes describe fixed wire layouts; their generated methods
are part of the checked API surface. Unknown future procedures are not silently
cast to a known command. Byte arrays and retained report collections are copied
or protected against mutation at the public boundary.

## Evidence and limits

See [verification evidence](docs/verification.md) and [release gates](docs/releasing.md).
Kotlin host conformance and an Android APK build do not imply Android runtime,
live Kotlin BLE interoperability or Bluetooth qualification. The published C and
TypeScript KICKR tests are separate evidence. No additional live equipment testing
is performed by this package's tests.
