# Coordinated FTMS libraries 1.0

Status: **preparation, not release-ready or published**. All nine ports target
their first stable `1.0.0` package release. Existing public versions remain in
the [release matrix](released-packages.md); do not install an unverified target.

## Scope and compatibility commitment

The common protocol basis is FTMS 1.0 with applicable errata documented in the
[specification audit](specification-audit.md). This is distinct from the package
version and from corpus schema/content identities. Existing corpus bytes and
comparison contracts are not changed by the milestone.

The baseline is each port's implemented raw `FullWire`, `CapabilityEvidence` and
`RangeInspection` surface. Preserve the optional modules listed in
[support profiles](support-profiles.md#current-package-claims); this milestone does
not require identical convenience APIs or new BLE integration. In particular,
Go's measurement normalization and record planning/assembly are not prerequisites
for this stable raw-codec scope. Swift remains revision-pinned; 1.0 does not claim
SwiftPM version-range resolution of language-prefixed tags.

For each stable port, public exports, documented behavior, error models, ownership
and supported toolchains are compatibility commitments. Review serialized reports
and exhaustive enum handling as well as callable functions. Backward-compatible
fixes use patch releases, additions use minor releases, and incompatible changes
use major releases. Ports may advance independently after this shared milestone.
Minimum-toolchain changes require an explicit documented compatibility decision.

## Audited starting point

Inspection base: `4b4685fed3eadcac0ef0330bcbe3b4bc930aab2d`.
Its [all-port CI run](https://github.com/deancochran/ftms/actions/runs/36915187383)
passed, including installed artifacts and site checks. That is evidence for the
existing 0.x source, **not** a stable-interface review or verification of 1.0 bytes.

| Port | Target tag | Work required before version promotion |
| --- | --- | --- |
| TypeScript | `typescript-v1.0.0` | Review public exports, legacy normalized behavior and raw diagnostics; replace the 0.x compatibility policy with the approved stable contract; verify new tag restrictions. |
| C | `c-v1.0.0` | Review public headers/layouts and caller-owned buffers; decide CMake/ABI compatibility policy; update VERSION, vcpkg recipe and distribution metadata together. |
| Swift | `swift-v1.0.0` | Review public values/errors and Swift 6/Apple deployment minima; retain and test revision-pinned consumers. |
| Kotlin/JVM | `kotlin-v1.0.0` | Review checked binary API baseline and generated data-class methods; verify Kotlin/Java/Android consumers and their version defaults. |
| Python | `python-v1.0.0` | Review public exports, typing and exceptions; replace alpha policy and metadata only after review; update pyproject/lockfile and verify wheel plus sdist. |
| Rust | `rust-v1.0.0` | Review public structs/enums, module paths, normalized views and buffer semantics; confirm MSRV, no_std and allocation guarantees; update Cargo manifest/lockfile together. |
| Dart | `dart-v1.0.0` | Review exports, immutable models, exception codes and JSON contracts; confirm SDK support and VM/browser/Flutter installed consumers. |
| Go | `packages/go/v1.0.0` | Review exported API and error/format behavior against the stable raw scope; reconcile full-parity roadmap wording; retain module path and verify the public proxy consumer. |
| C# | `csharp-v1.0.0` | Review public API across both TFMs; establish a deliberate API compatibility baseline; replace evolving-alpha policy and verify NativeAOT and signed public NuGet payloads. |

Every row remains **pending stable-interface review and final candidate checks**.
Missing optional modules are exclusions, not silent promises. Missing verification
for a claimed platform is a blocker or requires a narrower documented support claim.

## Execution gates

1. **Interface baseline.** Record the reviewed public surface for each port,
   accepted stability boundaries, supported toolchains and any breaking changes
   from its latest 0.x release. Retain existing API baselines; do not regenerate
   them merely to make a failing comparison pass. Add package-specific migration
   notes for actual changes; if none, record that after comparison.
2. **Candidate metadata.** Once the baseline review passes, set native package
   version authorities to 1.0.0 and update affected lockfiles, recipes, examples,
   classifiers and changelogs. Keep historical compatibility fixtures unchanged.
   Use a consistent package-guide summary: package version, protocol basis, wire
   profile, optional modules and publication state. Until publication completes,
   label the new version as a candidate and retain working current-release installs.
3. **Clean candidate verification.** Run all-package metadata readiness, actual
   language compilers/tests, complete corpus case accounting with exact hashes,
   installed-archive consumers and documentation checks on the reviewed commit.
   Retain each port's evidence; neither metadata readiness nor `pnpm verify`
   substitutes for native verification. Repeat checks after candidate changes.
4. **Publisher readiness.** Verify registry ownership, credentials/OIDC bindings,
   environments, protected tag patterns and signing requirements. TypeScript
   needs the new `typescript-v*` namespace protected and permitted, with an
   appropriate approval boundary before a 1.x candidate is merged or tagged;
   Go must retain its nested
   module prefix. Never infer remote configuration from workflow source.
5. **Independent publication.** Follow the [release process](releasing.md) and
   each package's runbook. Push only the approved exact tags, retain immutable
   identities, and stop the affected release on a failed gate. A coordinated
   milestone is not an atomic registry transaction. No retagging or overwriting.
6. **Public verification and documentation.** Verify downloaded artifacts and
   fresh installed consumers separately for all nine ports. Record tag/commit,
   checksums, run URLs and limitations in the release matrix. Only then change
   installation examples and site status to published 1.0.0. Mark the milestone
   complete only when all nine public-verification records exist.

## Evidence boundaries

Host conformance, embedded compilation, mobile application builds, real-device
execution and Bluetooth qualification are different claims. 1.0 promises the
reviewed library interface, not device compatibility, control authorization or
Bluetooth qualification. Existing physical-device limitations remain in force.

This preparation does not change published artifacts or authorize bypassing a
gate. Current 0.x manifests are deliberately retained until the interface reviews
are complete; the milestone target itself is not evidence of release readiness.
