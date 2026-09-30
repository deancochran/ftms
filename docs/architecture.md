# Cross-language FTMS architecture

Status: TypeScript, C, Swift and Kotlin have published bidirectional codecs,
range inspection and static capability interpretation. Python 0.1.0a2 is a
published alpha with bidirectional raw codecs, range inspection and static
capability evaluation; its convenience API remains language-specific and evolving.
Rust 0.1.0 is a released `no_std` crate with static capability interpretation,
normalized Feature/measurement views and record planning/assembly; only the newer
range/control/status projections and 97-case runner evidence are unreleased.
Dart is an implemented, unpublished full-wire source candidate with static
capability evidence, range inspection and normalized measurement views.
See the [canonical release matrix](released-packages.md) for versions and distribution
and [support profiles](support-profiles.md) for role-based direction claims; source
metadata is not publication evidence. This document defines boundaries, not
universal FTMS device compatibility.

## One protocol project, independent packages

Keep protocol decisions and cross-language regression evidence in one repository.
Consumers must be able to use one implementation without installing the others.
TypeScript, C, Swift, Kotlin, Python, Rust, and Dart occupy sibling directories under `packages/`.
The root manifest is private pnpm orchestration, not a publishable package;
`pnpm-workspace.yaml` includes the TypeScript package and private documentation
website under `site/`. The site's Node 22.12+ build requirement does not change
the protocol package's runtime requirements. Its npm
identity and public export paths remain stable. Source versions alone do not
establish publication; consult the release matrix above.

| Location | Responsibility | Current state |
| --- | --- | --- |
| `packages/typescript/` | TypeScript README, changelog, manifest, sources, tests, scripts, and compiler configs | Implemented |
| `shared/conformance/v1/` | Versioned, language-neutral codec vectors and schema | Existing regression corpus |
| `shared/conformance/README.md` | v1 comparison and runner-accounting contract | Existing documentation |
| `docs/support-profiles.md` | Role-based wire-direction and optional-module claims | Current package taxonomy |
| `shared/protocol/capability-discovery.md` | Shared static capability interpretation rules | Implemented independently by TypeScript, C, Swift, Kotlin and Python |
| `shared/conformance/capabilities/v1/` | Separate executable capability snapshots and exact report expectations | 63 shared cases |
| `shared/simulation/v1/` | Deterministic synthetic equipment traces | Host-only test evidence |
| `packages/c/` | C99 bidirectional codecs and capability interpreter usable from C++ | Released 0.2.0 source archive |
| `packages/swift/` | Native SwiftPM protocol package | Released 0.1.0 |
| `packages/kotlin/` | Kotlin/JVM library usable from Java and Android | Maven Central 0.1.0 |
| `packages/python/` | Pure synchronous Python protocol package | Published alpha 0.1.0a2 with static capability evidence |
| `packages/rust/` | Allocation-free `no_std` Rust protocol library and Cargo tooling | crates.io 0.1.0 released with capabilities, normalized Feature/measurement views and records; newer range/control/status projections are unreleased |
| `packages/dart/` | Pure Dart synchronous protocol codecs and static capability interpreter, usable from Flutter | Implemented 0.1.0 source candidate; not published on pub.dev |
| `examples/` | Installed-consumer and transport-boundary examples outside the core packages | Implemented host examples; limited device evidence is recorded separately |
| `site/` | Private Astro/Starlight presentation of canonical documentation | Static website; never published as a protocol package |

C# `DeanCochran.Ftms` 0.1.0-alpha.1 is published on NuGet with `FullWire`, range
inspection, capability interpretation and normalized views. Its
[release evidence](released-packages.md#published-prerelease-c-010-alpha1) records
actual public consumers; local metadata alone is not release evidence. Other future ports
remain deferred until a consumer justifies a specific support profile. The
existing TypeScript package continues to serve JavaScript and React Native consumers.

The C port has package-owned build, installation, verification and source-release
tooling. Its release does not establish vcpkg or ConanCenter registration.
Directory names for future ports are not promises of published artifacts.

Dart is a native language implementation, not a Flutter plugin or C wrapper. Its
manifest, sources, tests, development/release tools and documentation stay under
`packages/dart/`; no root pub workspace is needed. Test runners consume shared
assets directly; disposable browser test snapshots are generated from those exact
bytes, ignored and excluded from publication. The Dart package has no runtime
dependency on another port, Python schema tooling, Flutter or a BLE stack.

Swift Package Manager is an ecosystem exception: a conventional Git URL
dependency needs a repository-root `Package.swift`, even though Swift sources,
tests, documentation, and package-owned tooling remain under `packages/swift/`.
The implemented thin root manifest points into those directories. Swift uses
`swift-vVERSION` tag/revision pins rather than normal SwiftPM semantic-version
requirements. Release gates test an isolated public Git/tag consumer.

## Layers

The [shared layer](../shared/README.md) owns language-neutral definitions and
fixtures. Ports and their build/test tools depend on it; it depends on no port,
language-specific package, or tool. Definitions describe intended semantics;
fixtures record regression expectations, not an independently normative spec.
Root configs orchestrate the repository; per-package scripts own package builds
and distribution. Keep conventional root configs in place. Introduce `tools/`
only for real reusable tooling, not speculative infrastructure or npm-only scripts.

1. **Protocol codecs:** bytes to values and values to bytes; deterministic,
   transport-independent, with explicit units and malformed-input behavior.
2. **Capability interpretation (TypeScript, C, Swift and Kotlin implemented):**
   a pure evaluation of caller-supplied discovery/read evidence. Report declared
   capabilities, missing evidence, and contradictions. Do not scan, connect, read
   characteristics, or authorize motion.
3. **Integration examples:** show how callers feed BLE evidence into the above
   layers. Bluetooth dependencies and platform lifecycle belong here or in the
   consumer, never in the protocol packages.

The TypeScript aggregate API keeps the package's byte-only boundary: snapshots
carry only `Uint8Array`/`ArrayBuffer` read evidence and return normalized static
facts, not BLE callbacks or execution permission. C's aggregate capability API
uses an idiomatic pointer/count boundary; neither API allocates or claims control.

Do not infer a unique machine type from its name, manufacturer, or measurement
flags. A set of observed FTMS data characteristics is evidence, not machine
identity. Do not make Indoor Bike Data, ERG mode, or simulation mode prerequisites.

## Both ends of the wire

Port coverage must distinguish directions instead of labeling a package simply
"FTMS supported":

| Operation | Client (mobile app or bike computer) | Equipment/server |
| --- | --- | --- |
| Measurements, features, ranges, statuses | Decode | Encode |
| Control requests | Encode | Decode |
| Control responses | Decode | Encode |

Each package must audit and explicitly list its claimed directions; copying
client APIs is not a complete equipment-side implementation. GATT service
registration, subscriptions, encryption, permission ownership, and actuator
safety remain caller-owned.
The named [support profiles](support-profiles.md) turn these directions into
explicit package claims without requiring identical language interfaces.

## Shared behavior, idiomatic APIs

- Preserve wire integer widths, signedness, endianness, scaling, and sentinel
  behavior. Similar concepts can have different encodings in different
  characteristics; do not reuse a range layout for a control operand by analogy.
- Agree on normalized units, unknown/unavailable values, and diagnostics before
  writing a port. Use language-appropriate optional values and errors, not a
  literal translation of JavaScript objects or deprecated convenience aliases.
- Share independently reviewed protocol expectations and fixtures, not a
  mandatory runtime or foreign-function interface. Do not force C consumers to
  install Node, Swift consumers to install Rust, or Android consumers to use JNI.
- Retain specification provenance and applicable errata. The published
  `shared/conformance/v1/vectors.json` records the current basis. Do not redistribute
  local-only specification files as part of the scaffold.

## Conformance and release boundaries

Root build/test/package commands forward to TypeScript; root `pnpm verify` also
checks documentation and builds API reference HTML. Biome and Lefthook stay at the root.
TypeScript tests read the canonical shared corpus directly. Each TypeScript build
cleans generated outputs, compiles, and stages distribution snapshots of the
root `LICENSE` and `SECURITY.md` policies and the two canonical
`shared/conformance/v1` JSON assets into ignored child-package paths. The corpus
keeps its existing npm `conformance/v1` destinations and historical schema identity.
Package-owned `README.md` and `CHANGELOG.md` are tracked and survive clean/build;
the root README is a whole-project overview, not the npm API README. Snapshots are not
independently maintained copies. `prepack` runs the same build to ensure freshness.
The package verifier checks a linked consumer after a fresh build, before packing,
including all conformance exports. It also checks packed asset bytes against
their package/shared/root owners, the unchanged exact tarball file allowlist, source maps, and
the complete public exports map. Publishing and release-version validation target
the child manifest and changelog; the versioned corpus remains canonical in `shared/`.

Native runners should consume `shared/conformance/v1/schema.json` and `vectors.json`
 directly from a pinned source checkout/tag; npm is not required to obtain them.
 Do not copy and independently maintain fixtures inside each port. Document
 intentional platform limitations and numerical comparison rules; a subset run
 must not be presented as full conformance. Fixture reuse is not Bluetooth
 qualification and cannot substitute for independently checking the specification.
The [conformance runner contract](../shared/conformance/README.md) defines v1
comparison semantics, corpus identity, and explicit case accounting; it does not
provide or imply a universal executable harness.

See [coverage](coverage.md) for the audited current directions and evidence, and
[versioning](versioning.md) for independent package, specification, schema, and
content-revision boundaries.

Capability scenarios have an explicitly versioned executable schema and a
port-owned C runner under `shared/conformance/capabilities/v1` and `packages/c`,
respectively. They do not extend the existing codec v1 schema, whose shape and
identity are validated by TypeScript tests and the package verifier. Shared
template edits compress literal expectations; they do not depend on a port to
compute expected behavior.

Each implemented port owns local build/test commands, isolated consumer installation
checks, CI evidence, a supported-toolchain matrix and an independent package version.
Registry publishing requires separate approval; do not couple it to existing npm
tags without a deliberate release design. Root `pnpm verify` validates TypeScript
and documentation, not native package compilers or runtime evidence. The npm
packed-file allowlist continues to exclude repository-only native packages,
documentation and examples.

## Implementation sequence and acceptance

1. Review the [capability contract](../shared/protocol/capability-discovery.md) across all six
   machine-data families, including telemetry-only and contradictory evidence.
2. Turn reviewed scenarios into versioned shared fixtures and define coverage.
    The separate `shared/conformance/capabilities/v1` corpus now covers this
   static evidence boundary and does not modify codec corpus v1.
   Define coverage for both client and equipment codec directions.
3. For each new port, choose a role-based support profile, implement only claimed
   directions, and verify a real installed consumer without depending on another port.
4. Validate representative real equipment and mobile devices. Record model,
   firmware, platform, and results separately from host tests and simulations.

The adoption goal is replacement of handwritten FTMS codecs and capability
interpretation while preserving the consumer's Bluetooth stack. It is not
replacement of the entire trainer controller, nor universal device certification.
