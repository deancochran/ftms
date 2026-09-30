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
