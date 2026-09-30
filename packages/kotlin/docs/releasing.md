# Kotlin release gates

Kotlin is independently versioned. Proposed coordinates are
`io.github.deancochran:ftms:0.1.0`; a local Maven artifact is not a public release.
Kotlin release tags use `kotlin-vVERSION`, never the existing npm `v*` or C `c-v*`
tag namespaces.

## Verification before delivery

1. Run the complete package checks against canonical shared fixtures, including
   schema validation, literal encode/decode expectations, exact report comparisons,
   measurement layout matrix, and invalid-input tests. Record corpus hashes,
   comparison contracts, source commit and dirty state with complete accounting.
2. Run `bash verification/verify.sh` from the package (or invoke it by path from
   the repository). This includes isolated Maven-artifact Kotlin and Java callers
   and an Android APK build. Inspect all outputs, not just a successful compile.
3. Review the public API and package dependencies. Only the Kotlin standard library
   is intended as a runtime dependency; Gson/schema/JUnit dependencies are test-only.
4. Commit the verified source; rerun on the clean commit. Use that immutable commit
   for a release tag and artifacts. Do not alter shared contracts to make tests pass.

## Maven Central prerequisites

Publishing requires a Central Portal account authorized for the
`io.github.deancochran` namespace, a Portal publishing token, and an approved
signing key with its public key available as required by Central. GitHub access
does not imply Central access. Never put tokens or private keys in this repository
or console logs; provision them through a secret store or protected environment.

The release must include the binary, sources, documentation, complete POM metadata
(license, SCM, project and developer identity), signatures and required checksums.
Verify namespace ownership and signing identity rather than inventing either.
Upload only the artifact bytes already tested by isolated consumers. Confirm the
Portal reports `PUBLISHED`, then download and verify the public coordinates and
artifact digests before reporting Maven Central publication.

A GitHub release may distribute verified artifacts, but it must not be described
as Maven Central availability. Never substitute an empty JAR, unsigned placeholder
or incomplete protocol implementation to bypass a publication blocker.

## Evidence boundaries

JVM conformance, Android packaging, emulator execution and live Bluetooth exchange
are separate evidence. Release checks issue no equipment commands. Recorded
KICKR packets may be replayed offline; that does not imply a new live Kotlin test.

References:

- https://central.sonatype.org/publish/publish-portal-api/
- https://central.sonatype.org/publish/requirements/
- https://kotlinlang.org/docs/api-guidelines-backward-compatibility.html
- https://docs.gradle.org/current/userguide/publishing_maven.html
