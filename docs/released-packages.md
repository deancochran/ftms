# Released packages and executable examples

Last checked read-only against npm and GitHub: **2026-09-28**.
This is a point-in-time record, not a promise that branch source is published.

| Port | Public release verified | Runnable example | What is not released |
| --- | --- | --- | --- |
| TypeScript | npm `@deancochran/ftms@0.2.0`; GitHub `v0.2.0` | [TypeScript client](../examples/typescript-client/README.md) uses that exact version | New raw bidirectional APIs and aggregate capability interpreter |
| C / C++ | None | [Installed C client](../examples/c-client/README.md) tested with the local 0.1.0 source candidate | C source release, public vcpkg/Conan registry entries |
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
Until a release exists, use the explicitly labelled candidate instructions; do
not substitute a nonexistent public URL or claim registry availability.

## Publication blockers and next actions

- The accumulated changes are being delivered as a release-preparation PR,
  not a published release. Review, integration and green remote CI must precede
  publication. PR approval does not itself create a release tag.
- TypeScript source is prepared as the **0.3.0 candidate**, with a changelog entry
  for its new APIs. npm still serves 0.2.0; do not imply its capabilities changed.
- C requires its clean `c-vVERSION` release tag and successful artifact gates.
- The repository currently has **no configured environments**. The `c-release`
  environment named in the workflow must be created with required reviewers
  before a release tag is pushed; naming it in YAML alone does not add protection.
- vcpkg/Conan registry submissions are separate external actions after a real
  immutable artifact exists. Local recipe tests are not registry publication.

See [C release runbook](releasing-c.md) and [real-equipment test procedure](equipment-testing.md).
There are currently **no recorded real-equipment interoperability results**.
Do not advertise compatibility with specific equipment until reviewed evidence
names the actual model, firmware, platform and installed package version.
