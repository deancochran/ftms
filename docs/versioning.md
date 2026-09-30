# Versioning boundaries

FTMS specification text, corpus format/content, and each distributable package
have independent version histories. Do not synchronize them by implication.

| Boundary | Meaning | Current evidence |
| --- | --- | --- |
| Package semantic version | A package's public interface and distribution compatibility | TypeScript 0.4.0, C 0.2.0, Swift 0.1.0, Kotlin 0.1.0 and Python 0.1.0a1 are published independently; Rust 0.1.0 is an unpublished source candidate. Verified identities are tracked in [released packages](released-packages.md). Swift, Python and Rust use `swift-vVERSION`, `python-vVERSION` and `rust-vVERSION` tags respectively; Kotlin uses `kotlin-vVERSION` and Maven Central coordinates. |
| FTMS specification and errata | Bluetooth SIG service semantics and corrections used to review behavior | FTMS 1.0 plus ESR11 and EC23224 provenance; [1.0.1 annotated-redline reconciliation](specification-audit.md), with all nine incorporated errata attributed and remaining source conflicts explicitly recorded. |
| Corpus schema format | Shape and comparison rules for fixtures | `schemaVersion: 1`, under `shared/conformance/v1/`. |
| Corpus content revision | The exact schema/vector/contract bytes and checkout consumed by a runner | Pin immutable source commit, dirty indicator, and SHA-256 of both JSON assets plus `shared/conformance/README.md`. |
| Capability corpus format/content | Separate static-evidence schema and fixtures under `shared/conformance/capabilities/v1` | Report HEAD/dirty state and SHA-256 of schema, vectors, capability corpus README, and `shared/protocol/capability-discovery.md`; does not alter codec v1 identity or npm exports. |

## Existing v1 and npm history

Preserve v1's historical schema identity, including its `$id` path containing
`v0.2.0`, and preserve the existing TypeScript npm `v0.2.0` tag workflow. Neither
means that all future ports share an npm version, release at the same time, or use
the same package manager. No release automation is added by this policy.

An additive or corrected fixture can be a new corpus content revision while still
using schema format v1 when it needs no shape or comparison-rule change. An
incompatible fixture shape or comparator change requires a new schema version and
new corpus location; do not silently redefine v1. A correction to an expected
value requires specification/errata review, an explicit rationale, and tracking
of the correction across every implemented port's result. A passing old port is
not evidence that the old expectation was correct.

When a package's API or behavior changes, its maintainer applies that package's own
semantic-version policy and release evidence. A corpus-only correction does not
automatically require a synchronized package release, though an affected package
may need one. Conversely, a package release need not alter the corpus.

During the pre-release controls-v1 and capabilities-v1 milestone, the schema was
explicitly extended in place; that historical exception to the no-shape-change
rule above is not a forward-compatibility guarantee for earlier v1 runners. These
contracts must be consumed by exact schema/vector/contract hashes, not by
`schemaVersion` alone. Older strict schemas reject the new properties, and older
interpreters do not implement the C.7 comparison semantics. Consumers must upgrade
the schema and runner together. Once these corpus contracts are released as
stable, incompatible shape or interpretation changes require a new version and
location. This exception does not change the original published codec-v1 contract.

The controls-v1 command-profile extension is an optional case property that is
backward-compatible only in the direction of new runners reading old fixtures:
all prior fixtures retain their shape and omitted-format behavior,
and recursive exact comparison is unchanged. Its new schema/vector/contract
hashes identify this content revision. Consumers must validate the pinned schema
and execute the selected format; they must not ignore an unfamiliar property or
report unsupported selected cases as passing. The original codec-v1 E9135 edit
is a separately documented provenance correction, not changed expected values.

The capability corpus's C.7 change is observable behavior, not a provenance-only
or behavior-neutral revision. Legacy/default capability APIs supply unknown C.7
bonding/lifetime evidence; a present Feature then adds an insufficient-evidence
diagnostic, makes applicable operation prerequisites incomplete, and can require
larger diagnostic buffers. Consumers migrating to C.7-aware behavior must query
requirements using the same C.7 evidence and capacity assumptions as evaluation.
Explicit false/true C.7 evidence has the corresponding conditional Feature
property behavior; it does not grant connection or control permission.

The C package's `VERSION` file is its single source-version authority. CMake
reads it for the project, package config, and
pkg-config metadata. Its `ftmsConfigVersion.cmake` uses same-major-and-minor
compatibility: `0.x` minor versions are treated as potentially breaking. This is
local source-package metadata only, not a git tag, published artifact, or release
record.

## C# version identity

C# has an independent `packages/csharp/VERSION` authority and reserved
`csharp-vVERSION` tag namespace. Its initial source version is a NuGet prerelease,
not a public release. C# versions must already be canonical three-component
SemVer with lowercase prerelease labels and no build metadata, so NuGet
normalization cannot silently change the release identity. Registry publishing
requires separate authorization and verified ownership/trusted-publisher setup.
Local package validation never establishes public availability.

## C release policy

The C package is independently tagged `c-vVERSION`; existing `v*` npm tags remain
TypeScript-only and are not changed by C releases. A C release archive is built
only from a clean checkout at that exact tag. Building it is release evidence, not
a claim that a registry has published it. Conan and vcpkg registry submissions are
separate explicitly authorized pull requests after an immutable archive and digest
exist. Swift has a real implementation and thin root `Package.swift`. Its package
version is recorded in `packages/swift/VERSION`, with `swift-vVERSION` releases in
this same repository. SwiftPM's ordinary version resolver recognizes plain and
`v`-prefixed semantic versions, not an arbitrary `swift-v` namespace. Swift users
must therefore pin a **revision/tag or full commit**, not use normal version
ranges. The [Swift release gate](../packages/swift/RELEASING.md) verifies public
tag-pinned consumers on Linux/macOS plus Apple SDK builds before publication.
There is no separate distribution repository and no alteration of npm tags.

An illustrative release-evidence record (not an automated format) is:

```text
package: @example/ftms-swift 1.2.0
specification basis: FTMS 1.0 + EC23224
corpus: schemaVersion 1, source tag v0.2.0, schema sha256 <...>, vectors sha256 <...>
contract: shared/conformance/README.md sha256 <...>; checkout: commit <...>, dirty: false
evidence: host corpus 97/97; consumer install <result>; devices/PTS <separate record>
```

Corpus tests establish only the recorded codec regression expectations. They do
not guarantee interoperability, GATT lifecycle behavior, real-device operation,
PTS success, or Bluetooth qualification.
