# FTMS for Swift

Native Swift 6 FTMS 1.0 + EC23224 protocol/domain library, package version **0.1.0**.
Its [support profile](../../docs/support-profiles.md) is `FullWire`, with
`CapabilityEvidence`, `RangeInspection` and `NormalizedViews`; that claim includes
no BLE or execution authorization.
`Package.swift` is deliberately
thin; all Swift source and tests remain package-owned. The API accepts `[UInt8]`
and uses value types with explicit errors/diagnostics. It implements both codec
directions for six measurement families, Feature and the five ranges, all 21
Control Point procedures/responses, Machine/Training Status, and normalized
adapters for the codec-v1 corpus. It also provides `inspectRange`, which reports
the caller-selected layout and every defined candidate layout without inferring a
resistance format, and `evaluateCapabilities`, a static evidence interpreter for
Feature, ranges, characteristic properties, and all 21 Control Point opcodes.

## Scope

The core has no CoreBluetooth, BLE, timer, Combine, UI, lifecycle, permission,
or control-authorization dependency. Callers own discovery, subscriptions,
security, control ownership, response matching, and actuator safety.
`evaluateCapabilities` follows `shared/protocol/capability-discovery.md`, performs
no I/O, and deliberately does **not** expose a "can execute" result.

## Verification

Build with `swift build` and run native regressions with `swift test` at repository
root. For schema validation, content hashes, source identity, corpus accounting,
per-case marker reconciliation, and an isolated local-path consumer, use the full
verification command (from repository root):

```sh
python3 -m venv .build/swift-verification
.build/swift-verification/bin/pip install -r packages/swift/requirements-test.txt
.build/swift-verification/bin/python packages/swift/Verification/verify.py
```

The verifier persists its machine-readable result at
`.build/swift-verification-report.json`. It captures `swift test` output and only
marks a fixture passed after reconciling one post-assertion native marker for its
corpus/category/ID. A failing test process leaves every fixture explicitly
`unresolved`; missing, duplicate, or unknown markers are runner failures, never
implicit passes.

| Local evidence (Swift 6.0.3, Linux x86_64) | Result |
| --- | --- |
| Native test suite | 16 tests passed |
| Reconciled canonical fixtures | 282 / 282 passed; 0 failed, unsupported, skipped, or unresolved |
| Deterministic malformed-input exercise | 2,080 generated payloads across all measurement/range kinds, features, controls and statuses; no process traps |
| Directional raw assertions | Controls 72; measurements 47; statuses 63 |
| Measurement matrix | 181,760 structural, 46 sentinel, 47 reserved-flag, and 315 incomplete-prefix checks |
| Consumer installation | Passed through an isolated local-path SwiftPM consumer |

**Published-release evidence:** `swift-v0.1.0` passed the full native suite on
Linux (Swift 6.0.3) and macOS (Swift 6.1.2 / Xcode 16.4), plus independent public
tag consumers and macOS/iOS/tvOS/watchOS/visionOS SDK builds. The published
reports and checksums were downloaded and independently verified. See the
[release record](../../docs/released-packages.md#published-swift-010) for exact
source identity, hashes, CI history and verification boundaries.

Python and jsonschema are test tooling, not library dependencies. A Swift 6.0+
toolchain must be on PATH. Local verification used Swift 6.0.3 on Linux x86_64;
the official Ubuntu toolchain required local library compatibility shims on the
Arch-derived host. The Linux CI definition uses the matching Ubuntu toolchain
container instead. The macOS job selects Xcode 16.4 on macOS 15, runs the same
native suite and builds an isolated Git consumer against the Apple SDKs. Release
publication is blocked until both jobs pass for the tag; attached release reports
record the actual toolchain, source revision and SDK results.

Tests consume canonical files from
`shared/conformance` directly; they do not package fixture copies. They expand
the 63 capability input and expected-report templates independently and compare
the entire normalized report, and compare all 9 literal range-inspection reports.
Host results
are not Apple/iOS builds, BLE device interoperability, PTS, or qualification.
Swift package semantic versioning is independent of FTMS and corpus versions.
The report hashes every conformance-contract README, each validated schema and
instance, and the capability-discovery and wire-compatibility protocol contracts; capability case categories
come from the fixture's declared category rather than a generic `cases` bucket.

## Usage

Add the Git repository as a **revision-pinned** SwiftPM dependency and select the
`FTMS` product. The release tag is `swift-v0.1.0`:

```swift
dependencies: [
  .package(url: "https://github.com/deancochran/ftms.git", revision: "swift-v0.1.0")
],
targets: [
  .target(name: "YourTarget", dependencies: [.product(name: "FTMS", package: "ftms")])
]
```

For an immutable dependency pin, use the full release commit recorded on the
[release page](https://github.com/deancochran/ftms/releases/tag/swift-v0.1.0).
In Xcode, choose a **Commit** requirement with that full commit. Do not use a
normal version range (`from:` / `.exact()`): SwiftPM does not interpret the
`swift-v` prefix as an independent version namespace and the repository's `v*`
tags belong to npm. No registry submission or separate repository is required.
Local development can instead use `.package(path: "/path/to/ftms")`.

Swift 6.0+ is required. Declared Apple deployment minima are macOS 13, iOS 16,
tvOS 16, watchOS 9 and visionOS 1. CI verifies host execution on Linux/macOS and
SDK compilation of an installed library consumer for the other platforms; it
does not execute apps on each minimum OS version.

```swift
import FTMS

let request = ControlRequest(opcode: 5, operands: [75])
let bytes = try encodeControlRequest(request) // [0x05, 0x4b, 0x00]
// The application transports bytes; the codec never sends a command.
let response = try decodeControlResponse([0x80, 0x05, 0x01])
```

Raw operands preserve wire integers, not inferred percentages. Decoded ranges
and measurements retain their format options; pass matching options when encoding
an explicitly selected alternative. Normalization preserves unavailable values,
movement direction and unknown legacy pace units. Machine Status resistance is
always signed 16-bit tenths and does not inherit a Control Point format selection.

## Release and verification boundaries

The `Release Swift` workflow verifies the exact `swift-vVERSION` tag, clean source
on `main`, version/changelog, complete corpus reports and public tag-pinned
consumers before creating a GitHub release with checksummed evidence. See the
[release runbook](RELEASING.md). Source metadata or a CI definition alone does not
prove publication; see [verified releases](../../docs/released-packages.md).

There is no BLE integration, real-device Swift result, PTS result or Bluetooth
qualification evidence. Apple SDK compilation is not a claim of device runtime
testing, CoreBluetooth lifecycle correctness or safe control execution. C-only
packet planning/reassembly APIs are not included in this codec package.
