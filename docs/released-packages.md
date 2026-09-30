# Released packages and executable examples

Last checked read-only against npm and GitHub: **2026-09-29**.
Kotlin Maven Central publication and public consumers verified: **2026-09-30**.
This is a point-in-time record, not a promise that branch source is published.

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

Future Kotlin releases are automated by **Release Kotlin**: a reviewed
`packages/kotlin/VERSION`/changelog update merged to `main` runs the full gate,
creates the signed language-specific tag, publishes to Central and verifies public
consumers before completing its GitHub release. The persistent `maven-central`
environment holds the existing credentials/signing material; it does not require
repeating local integration setup for each version. Existing published versions
are verified without another upload. See the runbook for recovery and rotation.

## Current public packages

| Port | Public release verified | Runnable example | What is not released |
| --- | --- | --- | --- |
| TypeScript | npm `@deancochran/ftms@0.4.0` | [TypeScript client](../examples/typescript-client/README.md) retains its 0.2.0 compatibility baseline; isolated 0.4.0 inspection consumer also passed | Native implementations are separate packages, not npm exports |
| C / C++ | GitHub `c-v0.2.0` source archive | [Installed C client](../examples/c-client/README.md) and [passive replay](../examples/c-passive-replay/README.md) exercise installed artifacts | Public vcpkg/Conan registry availability is not established by this check |
| Swift | None | None | Implementation and SwiftPM release |
| Kotlin | Maven Central `io.github.deancochran:ftms:0.1.0` | Public-artifact Kotlin/Java execution and Android APK build; [consumers](../packages/kotlin/verification/README.md) | Kotlin Multiplatform, BLE transport and Android-runtime/device evidence |

## Start with the released TypeScript package

```sh
cd examples/typescript-client
npm install --ignore-scripts --no-audit --no-fund
npm start
```

The example decodes feature declarations, a supported power range, indoor-bike
and treadmill measurements, and constructs Request Control bytes without sending
them. It uses only APIs present in npm 0.2.0. It passed against a fresh registry
installation and separately against the current candidate tarball. Neither test
communicates with equipment.

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
