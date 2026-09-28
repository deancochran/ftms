# Cross-language FTMS architecture

Status: TypeScript has a published client release plus unreleased bidirectional
raw codecs and static capability interpretation. C has unreleased Feature/range
encoding/decoding, measurement/control/status codecs and static capability
interpretation. Swift/Kotlin remain scaffolds.
This document defines boundaries, not universal FTMS device compatibility.

## One protocol project, independent packages

Keep protocol decisions and cross-language regression evidence in one repository.
Consumers must be able to use one implementation without installing the others.
TypeScript, C, Swift, and Kotlin occupy sibling directories under `packages/`.
The root manifest is private pnpm orchestration, not a publishable package;
`pnpm-workspace.yaml` includes only the implemented TypeScript package. Its npm
identity and public export paths remain stable. Published TypeScript is
`@deancochran/ftms@0.2.0`; the next source candidate is `0.3.0`.

| Location | Responsibility | Current state |
| --- | --- | --- |
| `packages/typescript/` | TypeScript README, changelog, manifest, sources, tests, scripts, and compiler configs | Implemented |
| `shared/conformance/v1/` | Versioned, language-neutral codec vectors and schema | Existing regression corpus |
| `shared/conformance/README.md` | v1 comparison and runner-accounting contract | Existing documentation |
| `shared/protocol/capability-discovery.md` | Shared static capability interpretation rules | Implemented by C and TypeScript |
| `shared/conformance/capabilities/v1/` | Separate executable capability snapshots and exact report expectations | 49 shared cases |
| `packages/c/` | C99 bidirectional codecs and capability interpreter usable from C++ | Implemented protocol surface, unreleased |
| `packages/swift/` | Native Apple package | Reserved |
| `packages/kotlin/` | Kotlin/JVM library usable from Java and Android | Reserved |
| `examples/` | Future integration examples outside the core packages | Reserved |

Rust and other language ports are deferred. The existing TypeScript package
continues to serve JavaScript and React Native consumers.

The C port now has a narrow source implementation and port-local host tooling; it
remains unreleased and does not add a native package manifest, toolchain download,
or publishing job. Add each package's build and installation files
 with its first real implementation and tests. Directory names are not promises
 of registry names or published artifacts.

Swift Package Manager is the planned ecosystem exception: a conventional Git URL
dependency needs a repository-root `Package.swift`, even though Swift sources,
tests, documentation, and package-owned tooling remain under `packages/swift/`.
When Swift is implemented, prefer a thin root manifest that points into those
directories, or deliberately use a distribution repository instead. Do not add an
empty root manifest now. A future Swift release must test an isolated Git-URL
dependency, not only a local-directory build.

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
2. **Capability interpretation (C and TypeScript implemented):** a pure evaluation of caller-supplied
   discovery/read evidence. Report declared capabilities, missing evidence, and
   contradictions. Do not scan, connect, read characteristics, or authorize motion.
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

The current package emphasizes the client column. Native implementation work
must audit and explicitly list coverage; copying current client APIs is not a
complete equipment-side implementation. GATT service registration, subscriptions,
encryption, permission ownership, and actuator safety remain caller-owned.

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

Root pnpm commands forward to TypeScript; Biome and Lefthook stay at the root.
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

Each implemented port must gain its own local build/test commands, isolated
consumer installation test, CI checks, supported-toolchain matrix, and documented
package version before release. Registry publishing requires separate approval;
do not couple it to existing npm tags without a deliberate release design.

Until then, `pnpm verify` validates only the existing TypeScript package. Its
exact packed-file allowlist should continue to exclude repository-only native
scaffolds, documentation, and examples. Do not create green placeholder native
CI jobs that imply a compiler or device has been tested.

## Implementation sequence and acceptance

1. Review the [capability contract](../shared/protocol/capability-discovery.md) across all six
   machine-data families, including telemetry-only and contradictory evidence.
2. Turn reviewed scenarios into versioned shared fixtures and define coverage.
    The separate `shared/conformance/capabilities/v1` corpus now covers this
   static evidence boundary and does not modify codec corpus v1.
   Define coverage for both client and equipment codec directions.
3. Implement C with C++ consumption tests and a representative embedded
   cross-build; then Swift and Kotlin with native consumer tests.
4. Validate representative real equipment and mobile devices. Record model,
   firmware, platform, and results separately from host tests and simulations.

The adoption goal is replacement of handwritten FTMS codecs and capability
interpretation while preserving the consumer's Bluetooth stack. It is not
replacement of the entire trainer controller, nor universal device certification.
