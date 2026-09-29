# Released packages and executable examples

Last checked read-only against npm and GitHub: **2026-09-29**.
This is a point-in-time record, not a promise that branch source is published.

| Port | Public release verified | Runnable example | What is not released |
| --- | --- | --- | --- |
| TypeScript | npm `@deancochran/ftms@0.3.0` | [TypeScript client](../examples/typescript-client/README.md) retains its 0.2.0 compatibility baseline | Changes under Unreleased, including boundary hardening |
| C / C++ | GitHub `c-v0.1.0` source archive | [Installed C client](../examples/c-client/README.md) exercises installed artifacts | Public vcpkg/Conan registry availability is not established by this check |
| Swift | None | None | Implementation and SwiftPM release |
| Kotlin | None | None | Implementation and Maven Central release |

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
The public archive is at <https://github.com/deancochran/ftms/releases/tag/c-v0.1.0>.
Source availability does not establish package-manager registry publication.

## Verified release identity and next actions

- Both releases identify `74f1552959d96755f38eac42f6999a5b04088b2f`.
- npm 0.3.0 integrity and all seven included source files matched that checkout.
- C archive SHA-256 is
  `3dc61329a2883f88a7828cff77b282961c9e91680ecae0ca5100622e9d8e6924`;
  its checksum asset and ten source/header files matched the reviewed checkout.
- CI, Native C, Publish and Release C runs for that commit succeeded. This does
  not establish environment protection settings or device compatibility.
- Further changes require separate review, verification and explicit release
  approval. Updating this record does not publish a new version.
- vcpkg/Conan registry submissions are separate external actions after a real
  immutable artifact exists. Local recipe tests are not registry publication.

See [C release runbook](releasing-c.md) and [real-equipment test procedure](equipment-testing.md).
Local work now includes a [limited passive KICKR CORE pilot](equipment-results/2026-09-29-kickr-core-linux.md).
It is not evidence bundled into the already-published releases.
Do not advertise compatibility with specific equipment until reviewed evidence
names the actual model, firmware, platform and installed package version.
