# Versioning boundaries

FTMS specification text, corpus format/content, and each distributable package
have independent version histories. Do not synchronize them by implication.

| Boundary | Meaning | Current evidence |
| --- | --- | --- |
| Package semantic version | A package's public API and distribution compatibility | TypeScript has published `@deancochran/ftms` `0.2.0` and an unreleased `0.3.0` source candidate; C has an unreleased source-only `0.1.0` candidate in `packages/c/VERSION`; other native packages do not exist. |
| FTMS specification and errata | Bluetooth SIG service semantics and corrections used to review behavior | FTMS 1.0 plus recorded ESR11 and EC23224 provenance. |
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

The C candidate's `VERSION` file is its single package-version authority. CMake
reads it for the project, package config, and
pkg-config metadata. Its `ftmsConfigVersion.cmake` uses same-major-and-minor
compatibility: `0.x` minor versions are treated as potentially breaking. This is
local source-package metadata only, not a git tag, published artifact, or release
record.

## C release policy

The C package is independently tagged `c-vVERSION`; existing `v*` npm tags remain
TypeScript-only and are not changed by C releases. A C release archive is built
only from a clean checkout at that exact tag. Building it is release evidence, not
a claim that a registry has published it. Conan and vcpkg registry submissions are
separate explicitly authorized pull requests after an immutable archive and digest
exist. Swift remains independently versioned and tagged; no root `Package.swift`
is added until it has a real implementation.

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
