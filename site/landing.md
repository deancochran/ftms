# FTMS Protocol Libraries

## Your Bluetooth stack. Shared protocol foundations.

Replace handwritten Fitness Machine Service packet parsing with typed values,
explicit diagnostics, and bidirectional codecs. Build a fitness application,
embedded integration, or protocol tool without taking on another connection stack.

[Understand FTMS: from bytes to a workout](../docs/ftms-explained.md). See how eight
bytes become speed, cadence and power, how control messages work, and why a shared
codec saves applications from maintaining the same protocol logic.

| Build with | What you get | Start |
| --- | --- | --- |
| C | Portable C99 with C++ consumers, fixed-point values, caller-owned memory | [Install the source archive](../examples/c-client/README.md) |
| C# | Managed .NET codecs and capability evidence | [C# package guide](../packages/csharp/README.md) |
| Dart | Pure Dart codecs for Dart and Flutter applications | [Dart package guide](../packages/dart/README.md) |
| Go | Raw codecs and capability evidence for Go applications | [Go package guide](../packages/go/README.md) |
| Kotlin/JVM | Independent Kotlin and Java codecs and capabilities | [Kotlin package guide](../packages/kotlin/README.md) |
| Python | Synchronous codecs and static capability evidence | [Python package guide](../packages/python/README.md) |
| Rust | Allocation-free `no_std` codecs and normalized views | [Rust package guide](../packages/rust/README.md) |
| Swift | Native SwiftPM codecs and capabilities | [Swift package guide](../packages/swift/README.md) |
| TypeScript | JavaScript/TypeScript ESM, normalized metrics, raw codecs and declarations | [Run the quickstart](../examples/typescript-quickstart/README.md) |

See [current releases](../docs/released-packages.md) for verified versions and
prerelease status. The [planned 1.0 milestone](../docs/release-1.0.md) is not yet a
published family. [Choose a language](../packages/README.md) for a step-by-step entry point.

## A focused boundary

Decode measurements, features, ranges and statuses. Construct control messages.
Interpret capability evidence. Keep Bluetooth discovery, connections, permissions,
timeouts, procedure ownership and physical safety in your application.
The [consumer adapter seam](../docs/architecture.md#consumer-adapter-seam) gives
the complete project-wide ownership split.

**A valid packet is not permission to control equipment.** Host tests and shared
fixtures are evidence of tested behavior, not universal device compatibility or
Bluetooth qualification.

## Integrate with confidence

- [TypeScript and C cookbook](../docs/integration.md): choose the right public API for the task.
- [Transport recipes](../docs/transport-recipes.md): JavaScript and C byte-boundary examples.
- [Consumer adapter seam](../docs/architecture.md#consumer-adapter-seam): protocol-package and application ownership.
- [Releases and support](../docs/released-packages.md): distinguish source from published packages.
- [Support profiles](../docs/support-profiles.md): select client and equipment wire directions.
- [Protocol coverage](../docs/coverage.md): inspect tested scope and evidence limits.
- [Contributing](../CONTRIBUTING.md): report problems and improve the project.

MIT licensed. Created and maintained by Dean Cochran.
