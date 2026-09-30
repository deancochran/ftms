# Kotlin 0.1.0 verification

Public release verified **2026-09-30**: signed tag `kotlin-v0.1.0`, source commit
`1fdfefb62f5c1b6a6b3e757cf24deb9d5c09560a`. Final clean-source JUnit accounting:
**87 tests, zero failures/errors/skips**. All 30 Maven Central files matched the
signed manifest; signatures and public Kotlin/Java execution plus Android APK
compilation passed. See [release identities](../../../docs/released-packages.md)
for the deployment and artifact hashes. The publisher subsequently has 18 passing
offline safety regressions, including observed Portal status behavior.

Implementation source base: `8a0006671df3babf4276ed3a97607ef7bc4fd46e`.
Initial integrated verification was performed on the dirty `feat/kotlin-delivery`
checkout. Each runner records its actual HEAD/dirty state and exact corpus hashes;
the clean committed source must pass the same release gate before delivery.

## Conformance accounting

| Contract | Cases / assertions | Initial integrated result |
| --- | --- | --- |
| Original codec v1 | 97 cases | Passed, no skips |
| Raw values v1 | 8 cases / 16 directions | Passed |
| Raw controls v1 | 41 cases / 72 directions | Passed |
| Raw measurements v1 | 26 cases / 47 directions | Passed |
| Raw statuses v1 | 38 cases / 63 directions | Passed |
| Compatibility v1 | 9 cases / 18 directions | Passed |
| Range inspection v1 | 9 complete reports | Passed |
| Static capabilities v1 | 63 complete reports | Passed |
| Measurement matrix v1 | 181,760 layouts, each encoded and decoded | Passed |
| Sentinel / RFU / prefix boundaries | 46 / 47 / 315 | Passed |

The first integrated run had 85 JUnit tests, zero failures/errors/skips; corpus
assertion counts are not JUnit method counts. Additional review regression tests
reject action values on actionless machine statuses and overflowing Training
Status flags. Final JUnit XML is the authoritative test-method accounting.

All schema-bearing canonical corpora are validated against their checked-in
schemas. Inspection has no canonical schema, so its strict structural validator
is test-owned and identified separately. No fixtures are copied or changed.
Literal encoded bytes and decoded expected reports are independent assertions.
The original-v1 adapter implements its specified subset/numeric comparison;
additive raw and capability reports use exact comparisons.

Foundation reports are in `build/conformance/`; original/compatibility reports
are in `build/reports/conformance/`. Measurement, matrix, status and capability
reports are retained in JUnit XML standard output under `build/test-results/test/`.
These include the exact schema/vector/layout/contract SHA-256 identities and
case/direction outcomes. Do not substitute `schemaVersion: 1` for content identity.

Canonical original-v1 identities at the source base:

| Asset | SHA-256 |
| --- | --- |
| schema | `e6d976172a32e3124602d17e46ed5fbab337f4f1d6535aec85a83069637268e0` |
| vectors | `9b5b61353b191179cc629d8c459b2a185b9e03b7ce5f3f51b715520162e8a5c7` |
| comparison contract | `a2c67ddf007502de19aac88aafef345f6741d15c83e53dd6652e35a753ad706e` |

## Package and installation

Verified locally on Linux x86_64 with JDK 17, Kotlin 2.2.0 and Gradle 8.14.3:

- `explicitApi()` compilation and binary API baseline check.
- Local Maven publication: binary JAR, source JAR, Dokka documentation JAR,
  Gradle module metadata and POM. Runtime dependency: Kotlin stdlib 2.2.0 only.
- Independent Java and Kotlin builds compile **and execute** using the artifact.
  FTMS resolution is exclusive to the supplied file repository; refresh is forced
  to avoid validating a cached older artifact at the same version.
- Android APK build using AGP 8.10.1, min SDK 26 and compile/target SDK 35 passed.
  This is a packaging/compilation check, not an emulator or real-device run.
- Dependency locks, checksum verification metadata and wrapper checksum are
  package-owned. Binary/source archives use reproducible ordering/timestamps.
- The publishing client has a separate offline Python regression suite covering
  credential permissions, secret-free error reporting, redirect rejection, bundle
  integrity/path validation, clean-source requirements and two-phase deployment
  state handling. `verification/verify.sh` runs it before the JVM checks.

The standard release client signs a clean-commit manifest and the exact artifacts
tested by these consumers. Its separate public-verification stage compares all
published hashes/signatures and executes the same consumers against Maven Central.
See [release gates](releasing.md) for commands and evidence retention. Local tests
alone do not establish that a public upload has completed.

Run the complete gate with:

```sh
ANDROID_HOME=/path/to/android-sdk bash packages/kotlin/verification/verify.sh
```

## Review closure and boundaries

Independent review identified and corrected a JVM-visible mutable capability byte
accessor, insufficient capability fixture validation/expansion, and stale consumer
dependency-cache risk. A second review identified silent action loss in the Machine
Status encoder; explicit rejection and regression tests were added. Coordinator
inspection also added Training Status flag-width rejection.

No BLE transport, Android lifecycle, physical actuator policy, C packet planner,
record assembler or session simulator is included. The simulation harness is a
separate host policy, not a missing raw codec. No live Kotlin equipment commands
or power-accuracy tests ran. This package does not claim universal device support
or Bluetooth qualification. Maven Central publication requires separate recorded
public-artifact evidence; see [release gates](releasing.md).
