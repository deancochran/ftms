# FTMS packages

TypeScript **0.4.0**, C **0.2.0**, Swift **0.1.0** and Kotlin/JVM **0.1.0** are
published with bidirectional codecs, range inspection and static capability
interpretation. Python **0.1.0a1** is a published partial alpha with bidirectional
raw codecs and no capability evaluator; unreleased Python source now includes
static capability evaluation against the shared corpus. See the role-based
[support profiles](../docs/support-profiles.md) and exact
[release identities](../docs/released-packages.md); source metadata alone is not
publication evidence.

| Port | Initial consumers | Distribution status |
| --- | --- | --- |
| [TypeScript](typescript/README.md) ([source](typescript/src/)) | JavaScript, TypeScript, and React Native applications | npm: `@deancochran/ftms` |
| [C](c/README.md) | Embedded firmware and C++ applications | Released C99 source archive with CMake; Make tooling is source-checkout-only |
| [Swift](swift/README.md) | iOS and other supported Apple applications | SwiftPM `swift-v0.1.0` |
| [Kotlin](kotlin/README.md) | Android, Kotlin/JVM, and Java applications | Maven Central `io.github.deancochran:ftms:0.1.0` |
| [Go](go/README.md) | Go applications, gateways and protocol tools | Published Go module `github.com/deancochran/ftms/packages/go` v0.1.0 |
| [Python](python/README.md) | Python applications, tooling and protocol analysis | PyPI `deancochran-ftms` 0.1.0a1; evolving alpha |
| [Rust](rust/README.md) | Embedded firmware and Rust applications | crates.io: `ftms` 0.1.0; newer source capabilities unreleased |
| [Dart](dart/README.md) | Flutter applications and standalone Dart tools | `deancochran_ftms` 0.1.0 source candidate; not published on pub.dev |

Start from the [architecture](../docs/architecture.md) and the shared
[capability contract](../shared/protocol/capability-discovery.md). Capability coverage must
not require an indoor bike, a particular brand, or an application control mode.
Use the shared [conformance runner contract](../shared/conformance/README.md),
[coverage matrix](../docs/coverage.md), and [versioning boundaries](../docs/versioning.md)
when an implementation begins.

Keep each port's sources, manifest, tests, toolchain-specific files and
package-owned documentation within its directory. Reuse the canonical
`shared/conformance/v1/` corpus rather than copying
it. Add build manifests and CI with real implementations, not empty packages.
Do not infer future registry names, minimum platform versions or release dates
from a directory or deferred-port mention.

Rust 0.1.0 is released on crates.io with capability interpretation, record
assembly and normalized Feature/measurement views. Its unreleased source adds
range/control/status projections and 97-case evidence; see its
[coverage and evidence](rust/docs/verification.md).
C# is being implemented with an explicitly approved full-wire parity objective;
see its package-owned coverage and verification evidence before relying on a
particular module. Other future ports remain deferred until a consumer justifies
a specific support profile. The TypeScript npm build/release remains independent;
the private root pnpm workspace orchestrates TypeScript and the documentation site,
not native package builds.
Dart's requested full-wire port additionally implements static capability evidence,
range inspection and normalized measurement views. It has independent
[verification](dart/doc/verification.md) and [release gates](dart/RELEASING.md);
source/host evidence does not imply pub.dev publication or Flutter device testing.
Ports and package tooling consume the independent [shared layer](../shared/README.md),
which has no dependency on any port. TypeScript owns its npm staging/verification
scripts, API README, and changelog; root policy and orchestration remain at root.

Swift has one ecosystem exception: Swift Package Manager Git dependencies look
for the thin repository-root `Package.swift`, which points into package-owned
sources and tests under `packages/swift/`.
