# Kotlin / Java port

Status: reserved, not implemented. No Maven artifact is available to install.

## Intended package

- A Kotlin/JVM protocol library usable from both Android and Java callers.
- Byte-oriented APIs without Android framework, BLE library, or coroutine
  requirements in the core; optional integration belongs outside it.
- Java-friendly entry points and result types; explicitly handle signed JVM bytes
  and unsigned FTMS values rather than exposing accidental sign extension.
- Explicit units, unknown values, malformed-input diagnostics, and shared
  capability semantics for all six FTMS measurement families.

With the first implementation, add the Gradle build/settings, pinned wrapper,
`src/main/`, and `src/test/` here. Choose Kotlin, Java, Gradle, and Android consumer
baselines based on tested requirements. Kotlin Multiplatform is not part of this
initial commitment; Swift remains an independent native package.

## Required evidence before release

1. Run applicable shared vectors from `../../shared/conformance/v1/` with JVM tests.
2. Compile and run Kotlin and Java consumer tests, including unsigned-byte and
   unknown-value cases.
3. Verify isolated consumption from a local Maven artifact without installing
   Node, the C toolchain, or Swift.
4. Build an Android integration example using the documented baseline while
   keeping the core independent of the Android SDK.
5. Separate JVM tests, Android builds/emulator results, and real-device Bluetooth
   tests in the verification report.

See the [architecture](../../docs/architecture.md) and
[capability design](../../shared/protocol/capability-discovery.md). Connection management,
security, control acquisition, timeouts, and physical safety remain caller-owned.

This package will own its API docs and build/test tooling. It consumes the
independent shared layer; shared assets do not depend on Kotlin or its tools.
