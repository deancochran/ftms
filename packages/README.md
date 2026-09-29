# FTMS packages

Current source versions are TypeScript **0.4.0** and C **0.2.0**, with bidirectional
codecs, static capability interpretation and additive range inspection. Swift
and Kotlin remain README-only scaffolds. See [release identities](../docs/released-packages.md)
for verified publication status; source metadata alone is not publication evidence.

| Port | Initial consumers | Planned distribution |
| --- | --- | --- |
| [TypeScript](typescript/README.md) ([source](typescript/src/)) | JavaScript, TypeScript, and React Native applications | npm: `@deancochran/ftms` |
| [C](c/README.md) | Embedded firmware and C++ applications | Released C99 source archive; Make and CMake integration |
| [Swift](swift/README.md) | iOS and other supported Apple applications | Swift Package Manager |
| [Kotlin](kotlin/README.md) | Android, Kotlin/JVM, and Java applications | Maven artifact |

Start from the [architecture](../docs/architecture.md) and the shared
[capability contract](../shared/protocol/capability-discovery.md). Capability coverage must
not require an indoor bike, a particular brand, or an application control mode.
Use the shared [conformance runner contract](../shared/conformance/README.md),
[coverage matrix](../docs/coverage.md), and [versioning boundaries](../docs/versioning.md)
when an implementation begins.

Keep each port's future sources, manifest, tests, and toolchain-specific files
and package-owned documentation within its directory. Reuse the canonical
`shared/conformance/v1/` corpus rather than copying
it. Add build manifests and CI with real implementations, not empty packages.
No registry names, minimum platform versions, or native release dates are
committed by this scaffold.

The initial roadmap is C/C++ consumption, then Swift and Kotlin/Java. Rust and
 other ports remain deferred. The TypeScript npm build/release remains independent;
 the private root pnpm workspace orchestrates only that implemented package.
 Ports and package tooling consume the independent [shared layer](../shared/README.md),
 which has no dependency on any port. TypeScript owns its npm staging/verification
 scripts, API README, and changelog; root policy and orchestration remain at root.

Swift has one planned ecosystem exception: Swift Package Manager Git dependencies
look for a repository-root `Package.swift`. When real Swift code exists, a thin
root entrypoint may point into `packages/swift/`, or Swift may use a distribution
repository. Do not add a placeholder manifest; sources, tests, and package docs
remain in `packages/swift/`.
