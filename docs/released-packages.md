# Released packages and executable examples

Last checked read-only against npm and GitHub: **2026-09-29**.
This is a point-in-time record, not a promise that branch source is published.

This is the **canonical current release matrix** for this source tree. Other
guides link here rather than treating historical candidates as current releases.
Metadata was rechecked read-only during adoption work: npm `latest` and `gitHead`
still match the record below, and the C tag exposes the named archive and sidecar.
Work on other branches is not evidence of additional published implementations.

| Implementation | Recommended start | Requirements | Support/evidence boundary |
| --- | --- | --- | --- |
| TypeScript / JavaScript | [Current-release quickstart](../examples/typescript-quickstart/README.md) | Node.js 20+ for the quickstart; ESM; [package requirements](../packages/typescript/README.md#install) | [Security policy](../SECURITY.md); host/package checks do not validate every bundler or BLE stack |
| C / C++ | [Released-archive quickstart](../examples/c-client/README.md) | CMake 3.16+, C99 and compatible C++11 compiler for both example targets; [installation](../packages/c/INSTALL.md) | Source archive, not a universal binary; no registry registration or maintenance SLA implied |
| Swift / Kotlin | Unimplemented in this checkout | None established | No package from this source tree |

For source coverage see [coverage](coverage.md). For package, protocol and corpus
version distinctions see [versioning](versioning.md).

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

## Current public packages

| Port | Public release verified | Runnable example | What is not released |
| --- | --- | --- | --- |
| TypeScript | npm `@deancochran/ftms@0.4.0` | [Current quickstart](../examples/typescript-quickstart/README.md); [historical client](../examples/typescript-client/README.md) retains its 0.2.0 compatibility baseline | Native Swift/Kotlin implementations |
| C / C++ | GitHub `c-v0.2.0` source archive | [Installed C client](../examples/c-client/README.md) and [passive replay](../examples/c-passive-replay/README.md) exercise installed artifacts | Public vcpkg/Conan registry availability is not established by this check |
| Swift | None | None | Implementation and SwiftPM release |
| Kotlin | None | None | Implementation and Maven Central release |

## Start with the released TypeScript package

```sh
cd examples/typescript-quickstart
npm install --ignore-scripts --no-audit --no-fund
npm start
npm test
```

The quickstart asserts normalized indoor-bike metrics and truncation behavior.
Its recipe checks exercise features, power range, UUID dispatch, control codecs
and byte conversions without communicating with equipment. The separate 0.2.0
example remains a historical compatibility fixture, not the default entry point.

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
