# Original-v1 and compatibility Kotlin test adapters

These test-only adapters consume canonical `shared/conformance/` files directly.
They do not embed fixtures or use production output to construct expectations.
`CorpusTest` executes the complete original 97-case corpus and both directions of
each compatibility case (currently 9 cases / 18 directional assertions).

## Integration

The package test runtime needs JUnit Jupiter 5, Gson, and
`com.networknt:json-schema-validator:1.5.8` (including its Jackson transitive
dependency). The isolated verification used Kotlin 2.2.0/JVM 17, JUnit 5.11.4,
Gson 2.13.1, and networknt 1.5.8. Configure `useJUnitPlatform()` and the JUnit
Platform launcher runtime dependency in the package build.

Once production lanes are integrated, run from `packages/kotlin`:

```sh
./gradlew test --tests 'io.github.deancochran.ftms.legacy.*'
```

No production API changes were required. Imports target `Ftms.kt`'s raw features,
range, and control APIs plus `measurement/MeasurementCodec.kt` and
`status/StatusCodec.kt`. The API snapshots used for isolated verification were
copied into ignored `.context/legacy-verification/src/main/kotlin`; production
files were not modified. The temporary Gradle project uses the actual owned test
sources and canonical shared fixtures, rather than copies of fixtures.

Repository discovery ascends from the test working directory. A test JVM property
`ftms.repositoryRoot` can explicitly select the canonical checkout. Reports go to
`build/reports/conformance/{original-v1,compatibility-v1}.json`; the test JVM
property `ftms.reportDirectory` can override this output directory. Reports include
HEAD, dirty state, exact schema/vector/contract SHA-256 hashes, per-category
counts, every case/direction outcome, and runner errors. Schema/provenance failure
prevents case execution, records discovered cases as skipped with a reason, and
fails the suite. An unsupported operation fails rather than being dropped.

## Normalization contract

`Comparison.kt` implements the exact shared original-v1 comparison rules:
recursive exact objects; recursive subset objects with required keys; equal-length
ordered arrays in both modes; metric-only finite numeric tolerance strictly less
than 0.005; exact strings/null; diagnostic issue inclusion without ordering.
Extra metrics are allowed. Explicit null is distinct from a missing key, and zero
must be a number. JSON numeric representations such as `1` and `1.0` are equal.

`NormalizedAdapter.kt` documents its mappings in executable tables:

- Feature machine/target bits map in wire-bit order to all 34 named fields, plus
  the three historical aliases (`supportsERG`, `supportsSIM`,
  `supportsResistance`). No field is selected using fixture expectations.
- Range raw values divide by the decoded scale divisor. Decoded kind and unit
  map to historical names. Native LENGTH/RANGE errors map to `length`/`range`.
- Control request human-unit literals convert exactly through decimal arithmetic
  to raw integer operands. Response LENGTH/KIND failures, unknown requests, and
  unexpected parameters map to `malformed_response`. Unknown result evidence
  maps to `reserved_value`; successful spin-down speeds divide by 100.
- All 30 measurement slots map to named metrics with explicit divisors. Speed
  divides by 360 to m/s; cadence/stroke rate by 2; inclination/ramp/MET by 10;
  treadmill elevation and cross-trainer stride count by 10. Other slots retain
  raw whole units. Unavailable bits produce null. For truncated data, flagged but
  unread fields produce null using decoded flags, not fixture bytes. Cross-trainer
  direction maps to `forward`/`backward`.
- Status projection covers the canonical training/manual, target speed,
  simulation, and permission-lost semantics. Other labels remain explicitly
  unmapped rather than being borrowed from expectations. The decoded empty-machine
  evidence maps its unread status code to null. Diagnostic flags map to the shared
  snake-case issue codes, independently of expected issue lists.
- Compatibility decoding compares complete raw objects, including all 30 values,
  flags, masks, and byte count. Encoding constructs raw inputs from the literal
  expected object and compares every output byte. Selected resistance/pace formats
  are explicit and validated; unknown formats fail.

## Local verification evidence

At base `8a0006671df3babf4276ed3a97607ef7bc4fd46e` with dirty test additions,
the isolated Gradle project passed all 5 JUnit tests: 3 comparator tests and 2
complete corpus runners. Original-v1 passed 97/97; compatibility passed 18/18
directional assertions. Both reports had zero failed, unsupported, skipped, or
runner-error outcomes. The exact run reports are retained in ignored
`.context/legacy-verification/build/reports/conformance/`.

This is local host adapter evidence against contemporaneous production snapshots.
The integrating coordinator must run the package tests against integrated sources;
this run is not package installation, device, or Bluetooth qualification evidence.
