# C release and installation runbook

These are maintainer instructions, not authorization to execute remote actions.
C 0.2.0 is published as a GitHub source release whose bytes must not be replaced;
see the [canonical release matrix](released-packages.md) for verified identity and
platform evidence. Public Conan/vcpkg registry submission remains separate and
unverified. `packages/c/VERSION` owns the source version. npm and every other
language package keep independent tags and versions. These instructions apply to
a future approved release; do not recreate or overwrite an existing tag or release.

## Before integration

1. Review **all** tracked and untracked files in the candidate checkout. Keep
   machine-local `.context` and workspace guidance out of the product. Never stage
   build outputs, Conan caches or local tools.
2. Reconcile coverage: the later C packet planner and bounded record assembler
   are currently C-only. Raw codec
   and capability parity does not imply identical convenience APIs. Record
   intentional differences rather than claiming parity from historical tests.
3. Review the pre-1.0 public headers, VERSION, changelog, license and supported
   toolchains. Do not imply hardware qualification from host test results.
4. Prepare reviewable commits and a PR, then validate a clean checkout in CI.
   Committing, pushing and merging require explicit delivery authorization.

## Local verification

From the repository root:

```sh
env -u TMPDIR pnpm verify
make -C packages/c BUILD=build/release-readiness test
make -C packages/c BUILD=build/release-readiness check-embedded
python3 packages/c/scripts/verify-cmake.py
python3 packages/c/scripts/verify-source-bundle.py
```

Set `CMAKE` if the executable is not on PATH. The source verifier automatically
builds twice for deterministic-byte comparison, validates the exact file manifest
and checksum, then runs six C/C++ consumers from the extracted artifact:
relocated installation, `add_subdirectory` and checksum-pinned `FetchContent`.
CTest runs the consumer executables, including with multi-config generators.
It does not report merely rebuilding a library as a passing protocol test.

To verify an existing artifact **without replacing it**:

```sh
python3 packages/c/scripts/verify-source-bundle.py --archive /path/to/ftms-c-0.2.0.tar.gz
```

The SHA-256 sidecar must accompany it. `SOURCE.json` checks byte integrity and
provenance metadata; it is not a cryptographic signature or proof of publication.

## Package managers

Install verification tools into an isolated local environment. Conan 2.32.0 and
vcpkg source commit `58845ed63eb19aff55e896ea1f5d51f2a0df5b66` were tested locally.
vcpkg requires its normal host tools including zip/unzip/curl and may download
build helpers; neither workflow submits a package to a registry.

```sh
python3 packages/c/scripts/source-bundle.py
python3 packages/c/scripts/verify-package-managers.py \
  packages/c/build/source-candidate/ftms-c-0.2.0.tar.gz \
  --conan /path/to/conan --vcpkg /path/to/vcpkg
```

This uses a fresh Conan home with `--no-remote`, builds the **extracted artifact's
recipe**, and runs both C and C++ consumers. The vcpkg check is a Linux x64 overlay
verification, disables binary-cache reuse, installs the exact local archive with
SHA-512 verification and builds/runs both consumers. Missing tools fail; they do
not become skipped-success checks. The checked-in overlay reads
`FTMS_SOURCE_ARCHIVE` and `FTMS_SOURCE_ARCHIVE_SHA512` from the environment, set
by the helper. It is not itself a public-registry submission.

CI adds Linux package-manager checks and standalone source consumers on Linux,
macOS and Windows. C 0.2.0 passed that remote release matrix; future releases must
rerun it before claiming the same platform evidence.

## Merge and publication

1. Merge the reviewed, green PR to `main` only with explicit authorization.
2. Configure the GitHub **`c-release` environment with required reviewers and
   appropriate tag restrictions before pushing any release tag**. An environment
   name alone does not enable approval protection. Protect immutable release tags.
3. Review/update VERSION and the exact `## VERSION` changelog heading, then create
   and push `c-vVERSION` on the reviewed commit after separate release approval.
4. `.github/workflows/release-c.yml` verifies exact tag/version matching, clean
   checkout and main ancestry. It runs native/source checks and builds in explicit
   release mode. Candidate builds accept dirty source but cannot be used as
   release artifacts by the workflow or registry generator.
5. The **same uploaded archive** is downloaded and checked on Linux/macOS/Windows;
   Linux also tests Conan and vcpkg. Artifact SHA-256 travels between jobs and is
   checked again before release. Failed platform/package-manager jobs block release.
6. After environment approval, the workflow creates a GitHub release for the
   existing tag and uploads the tested archive/sidecar. A retry retains matching
   existing assets and may add missing verified assets. A tag-commit or digest
   mismatch fails; existing assets are never overwritten. Failed releases are
   investigated, not silently rewritten. No npm or registry publication is performed.

## Public registry submissions — separate delivery

After publishing the immutable GitHub artifact and confirming its URL resolves:

```sh
python3 packages/c/scripts/prepare-registry-recipes.py \
  /path/to/ftms-c-0.2.0.tar.gz --tag c-v0.2.0 \
  --output packages/c/build/public-vcpkg-ftms
```

The generator verifies the archive and requires clean release metadata. It emits
a complete versioned vcpkg manifest and public-URL recipe with the artifact's real
SHA-512. It does not invent a digest, claim the URL exists, overwrite output or
submit anything. Review/test the generated port against the published URL, then
open a separate PR to the curated vcpkg registry. Name availability and acceptance
are controlled by that registry.

The Conan recipe already supports local `conan create` of standalone source.
ConanCenter inclusion requires a separately reviewed center-style recipe/source
reference and upstream contribution; the included local recipe does not establish
ConanCenter availability. Do not advertise a public `conan install` or bare
`vcpkg install ftms` command until the chosen registry actually contains it.

## Other language distributions

Swift, Kotlin and Python now have independent release runbooks and public
artifacts. Their tags, registries and verification are not C release steps. See
[support profiles](support-profiles.md) and [released packages](released-packages.md).
Do not synchronize versions or repurpose another package's tags. New language
ports still require a named consumer, a real implementation and installed-package
verification before any publication work.
