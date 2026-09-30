# Released packages and executable examples

Last checked against npm, GitHub, Maven Central, PyPI, crates.io and the Go module proxy:
**2026-09-30 UTC**.
This is a point-in-time record, not a promise that branch source is published.

This is the **canonical current release matrix**. Begin with the
[current TypeScript quickstart](../examples/typescript-quickstart/README.md),
[C/C++ archive quickstart](../examples/c-client/README.md),
[Swift guide](../packages/swift/README.md), or
[Kotlin guide](../packages/kotlin/README.md).
The [Python package](../packages/python/README.md) is a published 0.1.0a2 alpha
with an evolving API and static capability evidence; see its release evidence below.
The [Rust crate](../packages/rust/README.md) is an implemented 0.1.0 source
candidate, but no `rust-v0.1.0` tag or crates.io package exists as of this check.
The [Dart package](../packages/dart/README.md) is published on pub.dev as
`deancochran_ftms` **0.1.0**; see its release evidence below.
Source, package, protocol and corpus versions are distinct; see [versioning](versioning.md).

## Published: Go v0.1.0

The public Go module proxy and checksum database serve
**`github.com/deancochran/ftms/packages/go@v0.1.0`**. The annotated tag
**`packages/go/v0.1.0`** identifies verified clean source
**`bb470e951694bbcaa092fad9a03a3c1c9bb6a757`**, merged into `main` by
[PR #26](https://github.com/deancochran/ftms/pull/26) at
`45e77b89b54d903932ad9b3da3edf929f4ea6324`. The tag identifies the reviewed source
commit, not the merge commit. No separate repository or root Go manifest is needed.

```sh
go get github.com/deancochran/ftms/packages/go@v0.1.0
```

- [Go CI](https://github.com/deancochran/ftms/actions/runs/36773096393) and
  [project CI](https://github.com/deancochran/ftms/actions/runs/36773097111) passed
  before merge. Local clean-source gates passed on Go **1.24.0** and **1.27.1**.
- Fresh public consumers on both toolchains downloaded through
  `proxy.golang.org` with `sum.golang.org` enabled, without `replace` or a workspace.
  Telemetry, control and capability code ran; downloaded-module tests/build and
  license verification passed independently of sibling shared fixtures.
- Public download provenance reports the exact repository, `packages/go` subdir,
  tag and source commit above. Module sum:
  `h1:Hmy4+bHNO3r0Tzs0Vpm5E04aWPv9wfSnhywjyDfM7vw=`.
  `go.mod` sum: `h1:ulbbeannQPoraddmBFBr7H6l2cxWlAINU8HEKtTDmoE=`.
  Module zip SHA-256:
  `907ee6e66d6b2eae75196831917a92735cc958a6eabea84ba20433743503fe9f`.
- All **63 capability cases** passed exact whole-report comparison with zero
  failed/unsupported/skipped cases. Additional gates passed 122 additive raw
  cases / 216 directional assertions, 9 range-inspection reports, 181,760
  structural layouts in both directions, 46 sentinel positions, 47 RFU cases,
  and 315 incomplete prefixes. Both bounded fuzz targets passed.
- The [GitHub release](https://github.com/deancochran/ftms/releases/tag/packages/go/v0.1.0)
  retains clean-source corpus identities, all four capability-contract hashes,
  public consumer evidence, matrix/inspection accounting, fuzz results and
  `SHA256SUMS`.
- [pkg.go.dev](https://pkg.go.dev/github.com/deancochran/ftms/packages/go@v0.1.0)
  displays the exact v0.1.0 package documentation and executable examples.

Scope is raw bidirectional codecs, range inspection, normalized ranges and static
capability interpretation. Normalized measurement views, original normalized
codec-v1 comparison, and record planning/assembly remain outside this release.
Minimum Go is 1.24; current executed consumer evidence is Linux/amd64. This does
not establish real-device interoperability, BLE lifecycle, physical-control
permission, or Bluetooth qualification. See the [Go guide](../packages/go/README.md),
[coverage](../packages/go/docs/coverage.md) and
[repeatable verification](../packages/go/docs/verification.md).

## Published: Dart 0.1.0

- Registry: <https://pub.dev/packages/deancochran_ftms/versions/0.1.0>.
- Source/tag: `dart-v0.1.0` identifies
  `3ca87a685942f942ef1f8c7af5681cf88371bc9b` (PR #23).
- Public archive SHA-256:
  `c3adbd9af2f67a274607b09a6cac997eea4bdac32dbdb7b7cef82e92fc0d50ed`.
- First publication used the authenticated maintainer CLI, as required for
  pub.dev bootstrap. The downloaded registry archive matched the verified file
  manifest; a fresh exact-version hosted consumer passed analysis, both public
  examples, and native compilation/execution.
- [Merged-source CI](https://github.com/deancochran/ftms/actions/runs/36760823865)
  passed the Linux/macOS/Windows minimum/current SDK matrix, JavaScript/Wasm
  browser tests and Flutter Android/iOS consumer builds. Local conformance covered
  all nine corpora, including 181,760 measurement layouts in both directions.
- GitHub environment `pub-dev` requires maintainer approval and allows only tags
  matching `dart-v*`. The maintainer confirmed pub.dev GitHub automation is set to
  repository `deancochran/ftms`, pattern `dart-v{{version}}`, required environment
  `pub-dev`, push events enabled and workflow-dispatch disabled. A future version
  will provide the first end-to-end OIDC publication evidence.
- The bootstrap tag's automatic release run is intentionally cancelled rather
  than uploading the already-published version again. Do not rerun that upload.
  Archived 0.1.0 documentation describes its pre-publication candidate state;
  this release matrix supersedes those historical status statements.
- Host and consumer checks do not establish real-device BLE interoperability or
  Bluetooth qualification.

## Published: TypeScript 0.4.0 / C 0.2.0

PR [#5](https://github.com/deancochran/ftms/pull/5) merged at
`a32de9c0b108bc55c9dc11752d928e959efd73ac`; both version tags identify that commit.
Local verification passed 588 TypeScript tests, the full native suite, package
consumers and Cortex-M0 compilation. CI, Native C, Publish and Release C all
completed successfully for the release commit. The public artifacts were then
downloaded and independently verified, not merely inferred from workflow status.

- npm **0.4.0** is the `latest` version; registry `gitHead` matches the release
  commit. SHA-512 integrity passed, its 42-file layout is preserved, and all seven
  published source files match. An isolated consumer of the downloaded artifact
  exercised range inspection and strict normalized numeric bounds successfully.
- C **0.2.0** archive SHA-256:
  `3aa60d809f3dcd02634417018d39f325c46a552734f0fe311ba748261914e61f`.
  The downloaded archive passed source-manifest verification and installed,
  vendored and FetchContent C/C++ consumers plus both repository examples.
- Remote release consumers passed on Linux, macOS and Windows; Conan/vcpkg
  recipes passed against the artifact. This is not public registry submission.
- PR CI initially exposed a hard-coded 0.1 CMake consumer request. The verifier
  now reads `VERSION`; the final PR/main/release runs passed. No failed gate was
  bypassed. GitHub emitted non-fatal Node-action deprecation warnings; migrating
  the pinned artifact actions is separate maintenance.

Repository examples are not included in the C source archive. Artifact tests
copy the repository examples into isolated consumer directories and link them
against the extracted/installed archive; they do not claim the archive ships them.

## Published: Kotlin/JVM 0.1.0

Maven Central now serves **`io.github.deancochran:ftms:0.1.0`**:
<https://repo.maven.apache.org/maven2/io/github/deancochran/ftms/0.1.0/>.
The signed annotated tag `kotlin-v0.1.0` identifies clean source commit
`1fdfefb62f5c1b6a6b3e757cf24deb9d5c09560a`, not the later PR merge commit.
Central deployment `86dfed11-b0e1-4795-a233-60e12e6fc12a` reached `PUBLISHED`.
The [GitHub release](https://github.com/deancochran/ftms/releases/tag/kotlin-v0.1.0)
retains the exact Central bundle, signed manifest, public key, publication receipts
and signed clean-source conformance reports.

- Clean-source gates: 87 JUnit tests, all applicable canonical corpora and
  181,760 measurement layouts encoded and decoded; all nine PR CI checks passed.
- Binary, sources, Dokka documentation, POM and Gradle module metadata were signed
  with OpenPGP fingerprint `A355E4B9EBD3FAEC850A84A6B7A6488FE4805547`. All ten staged
  artifacts/signatures matched the prepared manifest before the publish request.
- All **30 public files** (five artifacts, signatures and checksum sidecars) were
  downloaded and matched the signed manifest. Signatures verified. Independent
  Kotlin and Java consumers executed and the Android consumer built an APK with
  FTMS resolution exclusive to the public Maven Central repository.
- The Portal returned the exact Maven PURL at `VALIDATED` but empty PURL lists at
  `PUBLISHING`/`PUBLISHED`. A follow-up client fix handles that observed behavior
  without weakening the pre-publish coordinate/staged-byte checks. It has 18
  passing offline publishing-safety tests. No artifact or tag was replaced.

| Artifact | Verified SHA-256 |
| --- | --- |
| Binary JAR | `c32c3d4bf2533c0d5ff20cc30778973e0c1fd9568a7e75c505a6db0cbaf6a650` |
| Sources JAR | `cbbc3b3363125c7501ff45eb0780f6bfe21747988ccd015452c7bf126afaa8b7` |
| Documentation JAR | `b940124bbf6684b37b2333a8178ea4250a8c0243b1af688f8bae99a23ce4771a` |
| Central upload bundle | `f56b8db378ab1efb7242126fbbed42fef7d1761c9a2316e735d8c2c3a126eb25` |

The repeatable, explicit `prepare → upload → publish → verify` process and
credential/key maintenance are documented in the
[Kotlin release runbook](../packages/kotlin/docs/releasing.md). Kotlin package
version, FTMS protocol revision and corpus identity remain independent. This is
host/artifact and Android-build evidence, not a live Kotlin BLE or Android-runtime
test, physical accuracy result, or Bluetooth qualification.

Future Kotlin releases are automated by **Release Kotlin** after a maintainer
pushes the matching signed annotated `kotlin-vVERSION` tag on a reviewed `main`
commit. Merging a version/changelog update does not publish. The tag workflow runs
the full gate, publishes to Central and verifies public consumers before completing
its GitHub release. The persistent `maven-central`
environment holds the existing credentials/signing material; it does not require
repeating local integration setup for each version. Existing published versions
are verified without another upload. See the runbook for recovery and rotation.

## Published: Swift 0.1.0

Verified against public GitHub release assets and a fresh public-tag SwiftPM
consumer on **2026-09-30**. Implementation [PR #7](https://github.com/deancochran/ftms/pull/7)
and release-hardening [PR #8](https://github.com/deancochran/ftms/pull/8) are merged.
The annotated tag **`swift-v0.1.0`** identifies
**`a18009d6e9892d92bba00e3c6c6388a9fbc0f5c8`**. No existing npm/C tag or artifact
was changed and no separate repository was created.

- [Release Swift run 36662538259](https://github.com/deancochran/ftms/actions/runs/36662538259)
  succeeded, including tag identity, clean-source/main ancestry, complete corpus
  identity checks, Linux/macOS native verification and public **tag-pinned** consumers.
- Both hosts passed 16 native tests and all **282** canonical fixture IDs with
  zero failures, skips, unsupported or unresolved cases. The shared measurement
  matrix passed **181,760** layouts, 46 sentinels, 47 RFU cases and 315 incomplete
  prefixes. A deterministic 2,080-payload malformed-input exercise did not trap.
- Linux used Swift **6.0.3**; macOS used Apple Swift **6.1.2**, Xcode **16.4 (16F6)**.
  Installed-consumer release builds passed for **macOS 13, iOS 16, tvOS 16,
  watchOS 9 and visionOS 1** deployment targets. The reports retain resolved Git
  identities, SDK inventory, toolchains and canonical schema/vector/contract hashes.
- Downloaded all four public JSON reports and verified **SHA256SUMS** and every
  reported canonical-file hash against the tagged source. A second fresh public
  tag consumer on Linux compiled and ran after publication, resolving the exact
  commit above.
- Early gates exposed a local consumer's missing macOS minimum, hidden artifact
  upload filtering, incomplete older Xcode platform components and Git line-ending
  attributes that made clean checkouts appear dirty. All were fixed before the
  tag. The generated Kotlin launcher bytes were preserved unchanged. CI now
  requires clean evidence; no failed gate was bypassed. Pinned artifact actions
  still emit non-fatal Node-runtime deprecation notices.

| Public evidence asset | Verified SHA-256 |
| --- | --- |
| `swift-linux-verification.json` | `a96c426d6e98df20263bdcbdcd3ee9f8ff70f61b6a48f9b34f63c772d4c0b9f7` |
| `swift-linux-consumer.json` | `0fb205e5ad9854e0849c95d6e7a126f2b8a6298e920253fa5123c86473d3f59c` |
| `swift-apple-verification.json` | `0587679c91659c967378ecd4c341f6b5d4ec479904e4b7b6edb10c48c3a1640c` |
| `swift-apple-consumer.json` | `f5b0705208f62c49d1e31399e9f4a1370b93b59de90adfba9be47931aeeecf0d` |

Use `.package(url: "https://github.com/deancochran/ftms.git", revision: "swift-v0.1.0")`
and product `FTMS`; use the full commit above for an immutable pin. Normal
SwiftPM version requirements are intentionally unsupported because ordinary
`v*` tags in this repository identify npm releases. This is native compiler,
host-runtime and SDK-build evidence, **not** Swift BLE device interoperability,
runtime coverage of every Apple OS version, physical accuracy or Bluetooth qualification.
See the [Swift release runbook](../packages/swift/RELEASING.md).

## Published alpha: Python 0.1.0a2

PyPI serves **`deancochran-ftms==0.1.0a2`** at
<https://pypi.org/project/deancochran-ftms/0.1.0a2/>. Published and verified on
**2026-09-30** from annotated tag `python-v0.1.0a2`, identifying clean source commit
`82d978fa980fc4c5629fbdd855af42126f49bcef`. Implementation
[PR #25](https://github.com/deancochran/ftms/pull/25) is merged. The
[release workflow](https://github.com/deancochran/ftms/actions/runs/36761554741)
passed verification, published through the approved `pypi` environment using
Trusted Publishing and attestations, and completed public-artifact verification.

| Public artifact | Verified PyPI SHA-256 |
| --- | --- |
| `deancochran_ftms-0.1.0a2-py3-none-any.whl` | `b9a1feb44140f52c32ecfcb1841d41cfa05ea0627b4361706f6934179cdc60a8` |
| `deancochran_ftms-0.1.0a2.tar.gz` | `5261fa144e0f58ebe95d819ad276a269492abb22cb12c9248e42a774e04972bd` |

Both public files were downloaded and matched the exact verified build hashes.
Independent non-editable wheel and sdist consumers passed on Python **3.11.16**,
including feature/control/measurement codecs, capability enum exports and
explicit signed-tenths resistance evaluation. The workflow retains
`python-public-evidence-82d978fa980fc4c5629fbdd855af42126f49bcef`, whose
`public-package-verification-report.json` reports `complete: true` and no errors.

The release passed **169 tests on each of Python 3.11 and 3.14**, all scoped codec
corpora, the 181,760-layout measurement matrix, and **63/63** exact capability
cases with zero failed, unsupported or skipped cases. Capability schema version 1
and comparison inputs consumed by this release have these SHA-256 identities:

| Capability corpus / comparison input | SHA-256 |
| --- | --- |
| `shared/conformance/capabilities/v1/schema.json` | `1a23dd523896d41b6aa115eea906e6f899a9cfcc8008a87d133ba8c51409ef26` |
| `shared/conformance/capabilities/v1/vectors.json` | `90a9b85e735455515c36fc089fa786bd928e217e81cf95f5ccef67c0d479d3dd` |
| `shared/conformance/capabilities/README.md` | `e844292d9a916aa63db9d1f6d22de5525c1923e3584afbcc5013d93d374e6a6a` |
| `shared/protocol/capability-discovery.md` | `541ddd5950999bcd048808fd6eff578dc0a7031eaaa0dc988f8711003ecd488f` |

The alpha adds `CapabilityEvidence` to existing `FullWire` raw codecs,
`RangeInspection` and selected `NormalizedViews`. It does not add a normalized
control encoder, record planning/assembly, BLE transport or execution authority.
These are host/artifact results, not device interoperability or qualification.

### Published alpha: Python 0.1.0a1

Historical release evidence; superseded by 0.1.0a2 above.

PyPI serves **`deancochran-ftms==0.1.0a1`** at
<https://pypi.org/project/deancochran-ftms/0.1.0a1/>. The annotated tag
`python-v0.1.0a1` identifies clean source commit
`f556d9f9d6e5fc253c1ac9bd4564ea30ad97c26d`. The tag's
[Python verification and release run](https://github.com/deancochran/ftms/actions/runs/36662102567)
completed successfully and published the verified wheel and source distribution
through PyPI Trusted Publishing.

| Public artifact | Verified PyPI SHA-256 |
| --- | --- |
| `deancochran_ftms-0.1.0a1-py3-none-any.whl` | `3cd84fee28c3e8b2968d4fcbf9451c343b1b72e949e22797fc52d2deae8bf4b0` |
| `deancochran_ftms-0.1.0a1.tar.gz` | `0f434f7e3b14f499815367f028cb7af1744d9bc5156c80f364cc21b7a1190de4` |

The release is an explicitly selected pre-release with an evolving interface.
It provides bidirectional raw Feature, range, control, measurement and status
codecs plus selected normalized views and range inspection. It does not provide
static capability evaluation, BLE integration, lifecycle policy or execution
permission. Host and package verification are not real-device evidence. The
release workflow now includes a post-publication public-artifact hash and isolated
consumer job for future Python tags. A read-only rerun downloaded both artifacts,
matched the hashes above and executed independent isolated wheel and sdist
consumers on Python 3.11.15; both completed successfully.

## Implemented source candidate: Rust 0.1.0 (not published)

PR [#14](https://github.com/deancochran/ftms/pull/14) merged the independent,
allocation-free `no_std` Rust implementation at
`384f7304b6e5add0cee495c983928cc65c17a31b`. Its `Cargo.toml` declares 0.1.0,
but source metadata is not a release: there is no `rust-v0.1.0` tag, crates.io
package or Rust GitHub release. The crates.io API returned not found during this
read-only check.

The candidate implements `FullWire` raw codecs and `RangeInspection`; it does not
implement capability interpretation, normalized views, fragment planning/assembly,
BLE, device runtime or control authorization. See the package's
[verification record](../packages/rust/docs/verification.md) for exact host,
corpus, Cortex-M0 compile-only and packed-consumer evidence. Do not use a registry
installation instruction until this matrix records a verified public artifact.

## Current public packages

| Port | Public release verified | Runnable example | What is not released |
| --- | --- | --- | --- |
| TypeScript | npm `@deancochran/ftms@0.4.0` | [Current quickstart](../examples/typescript-quickstart/README.md); the separate client preserves a 0.2.0 compatibility baseline | Native implementations are separate packages, not npm exports |
| C / C++ | GitHub `c-v0.2.0` source archive | [Installed C client](../examples/c-client/README.md) and [passive replay](../examples/c-passive-replay/README.md) exercise installed artifacts | Public vcpkg/Conan registry availability is not established by this check |
| Swift | GitHub/SwiftPM `swift-v0.1.0` | Public tag-pinned Linux/macOS consumers and Apple SDK builds | BLE integration and Apple-device runtime evidence |
| Kotlin | Maven Central `io.github.deancochran:ftms:0.1.0` | Public-artifact Kotlin/Java execution and Android APK build; [consumers](../packages/kotlin/verification/README.md) | Kotlin Multiplatform, BLE transport and Android-runtime/device evidence |
| Python | PyPI `deancochran-ftms==0.1.0a2` | Verified public wheel/sdist consumers including capability evaluation; no repository BLE example | Stable interface and live-device evidence |

## Start with the released TypeScript package

```sh
cd examples/typescript-quickstart
npm install --ignore-scripts --no-audit --no-fund
npm start
npm test
```

The current-release quickstart asserts normalized metrics, truncation behavior,
capabilities, ranges and byte conversions without communicating with equipment.
The separate `typescript-client` example preserves the historical npm 0.2.0 baseline.

## C installation evidence

The C example uses `find_package(ftms CONFIG REQUIRED)` against an installed
artifact, not private source paths. The source-package verifier builds/installs
the archive, moves its prefix and runs the example from an isolated copy.
The public archive is at <https://github.com/deancochran/ftms/releases/tag/c-v0.2.0>.
Source availability does not establish package-manager registry publication.

## Historical baseline identity and next actions

- Previous npm 0.3.0 and C 0.1.0 releases identify `74f1552959d96755f38eac42f6999a5b04088b2f`.
- npm 0.3.0 integrity and all seven included source files matched that checkout.
- Previous C 0.1.0 archive SHA-256 is
  `3dc61329a2883f88a7828cff77b282961c9e91680ecae0ca5100622e9d8e6924`;
  its checksum asset and ten source/header files matched the reviewed checkout.
- CI, Native C, Publish and Release C runs for that commit succeeded. This does
  not establish environment protection settings or device compatibility.
- Further changes require separate review, verification and explicit release
  approval. Updating this record does not publish a new version.
- vcpkg/Conan registry submissions are separate external actions after a real
  immutable artifact exists. Local recipe tests are not registry publication.

See [C release runbook](releasing-c.md) and [real-equipment test procedure](equipment-testing.md).
The repository includes a [limited passive KICKR CORE pilot](equipment-results/2026-09-29-kickr-core-linux.md).
It used the earlier local 0.1.0-based C installation, not the newly published
0.2.0 artifact. Publication and host replay do not expand that device evidence.
Do not advertise compatibility with specific equipment until reviewed evidence
names the actual model, firmware, platform and installed package version.
