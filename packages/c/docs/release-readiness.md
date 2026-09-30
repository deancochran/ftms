# Local C release-readiness evidence — 2026-09-28

> Historical 0.1.0 candidate evidence for the checkout identified below, not
> current publication status. See the [release matrix](../../../docs/released-packages.md).

Branch `scaffold/native-capabilities`, HEAD/base
`41023a60cff6efdeef5e36730c3d7356a91d26b6`, intentionally dirty checkout.
No commit, merge, push, tag, GitHub release, registry submission or remote CI run
was performed. Existing protocol source/header changes were preserved; this
milestone changes packaging, verification and release documentation/workflows.

## Final artifact

Candidate: `packages/c/build/source-candidate/ftms-c-0.1.0.tar.gz`

SHA-256: `42acb1de5c615b1e7240c5415db2764ac6be818f63ce0326523444328c78a40f`

This is a **local candidate**, not a published artifact. SOURCE.json reports
`dirty: true`, `releaseArtifact: false`, `releaseTag: null`, `released: false`.
Every bundled file is hashed, and the sidecar hashes the entire archive. The
manifest is integrity/provenance metadata, not a signature. Its README is sourced
from package-owned INSTALL.md; CHANGELOG.md and the Conan recipe are included.

## Executed checks

- `make -C packages/c BUILD=build/release-final test`: native strict/sanitizer,
  corpus, fuzz, planner/record, installed consumers and source verification passed.
  Original codec corpus 97/97; capabilities 49/49; bidirectional assertions 188/188.
- `make ... check-embedded`: Cortex-M0 compile-only checks passed.
- `python3 packages/c/scripts/verify-cmake.py`: GCC/Clang installed and relocated
  C/C++ consumers, pkg-config and existing source-consumer checks passed.
- `python3 packages/c/scripts/verify-source-bundle.py`: deterministic double build,
  manifest/sidecar checks and **six actual C/C++ consumer executions** passed for
  installation/relocation, add_subdirectory and checksum-pinned FetchContent.
- Repeated exact-artifact verification with `CC=clang CXX=clang++`: all six
  consumer executions passed against the same final archive bytes.
- `verify-package-managers.py ARCHIVE --conan ... --vcpkg ...`: passed against the
  **final archive**, using fresh Conan home and local vcpkg install root. Conan
  built the extracted recipe with `--no-remote`; both managers compiled and ran
  C/C++ consumers. vcpkg binary-cache reuse was disabled.
- Nine source-bundle safety/regression tests passed: valid manifest, corrupt bytes,
  sidecar filename, wrong digest/extra file, duplicates, unsafe paths/links, version
  consistency, release metadata/clean tag guards, and public recipe generation.
  Negative test artifacts had recomputed checksums so deeper validation was tested.
- `env -u TMPDIR pnpm verify`: passed, 512 tests and original 97/97 codec vectors;
  lint, types, build and unchanged 42-file npm allowlist/consumer checks passed.
- Workflow YAML parsed locally; `git diff --check` passed.

Local tools: GCC 16.2.1, Clang 22.1.8, CMake 3.22.1, Conan 2.32.0, vcpkg source
`58845ed63eb19aff55e896ea1f5d51f2a0df5b66` (tool version 2026-09-26).
Conan and its dependencies were installed into an ignored package-local venv;
vcpkg and a missing zip utility were obtained into ignored build directories.
No system package install, global Conan profile or registry account was changed.

## Failures corrected

- Initial workflows had unsafe dispatch interpolation, wrong checksum working
  directory, missing repository context for gh and no platform artifact gates.
  Replaced with tag-only, pinned-action jobs and exact-artifact checksum outputs.
- Initial consumer verification assumed Unix executable paths and did not test
  the later release-mode bytes. It now accepts an exact archive and runs CTest
  consumer executables with Release configuration on multi-config generators.
- Removed a build-only CTest from the library itself; rebuilding a library is not
  a substitute for executing a consumer or protocol test.
- Fixed Conan's working-directory-dependent VERSION load and test executables,
  vcpkg source-root stripping/dependencies/environment inputs, and portable tar
  member paths. Actual package-manager installs validated the corrected recipes.
- Local vcpkg bootstrap initially failed because zip was absent; provided the
  distro zip executable in the isolated tools directory and reran successfully.
- A final-suite attempt put the Conan-only venv first on PATH, hiding host
  jsonschema. Reran with system Python for conformance and an explicit Conan
  executable; the complete native suite then passed.
- Independent review identified stale artifact evidence after installation-doc
  changes. Rebuilt and repeated GCC/Clang and both package-manager checks for the
  final hash above; older candidate hashes are not the delivery evidence.

## Remaining gates

Windows/macOS standalone consumers are implemented in CI but not executed here.
The real tag-gated release path, protected-environment approval and remote jobs
remain unexecuted. Configure required reviewers on `c-release` before pushing a
tag; merely naming an environment does not create an approval requirement.

The checked-in vcpkg overlay is for local verification. A generator now emits a
public recipe only from a verified clean tagged release artifact, but publication,
URL availability and curated-registry acceptance remain separate actions. Conan
source packaging is locally verified; ConanCenter submission is not performed.
No public package availability, hardware execution, BLE interoperability or
Bluetooth qualification follows from these host results. Swift/Kotlin remain
unimplemented scaffolds. The later C planner/assembler is documented as C-only.

See `docs/releasing-c.md` at repository root for integration and release steps.
Ignored local logs: `build/release-final.log`, `release-embedded.log`,
`release-cmake.log`, `source-release-check.log`, `release-clang-artifact.log`,
`package-managers-final.log`, and `release-typescript.log`.
